"""
AIWW.com 采集器 v1.0
采集国内AI工具关注度排行榜，提供真实的热度指标（日均关注人次）

数据源：
- 完整榜单：/aitoplist/all - top20
- 分类页面：/aitoplist/{category} - 每分类top10-13
- 工具详情：/aitool/{slug} - 获取完整信息

HTML结构（排行榜页面）:
  li.item.rank-N
    .rank > .num (排名)
    .rank > .change (排名变化: "-" 持平, 数字=变化位数)
    a.img-box > img (图标)
    .info-title > a.tt (工具名)
    .info-title > .organization (公司)
    .info-desc > p (描述)
    .num-change > i.iconfont (icon-increase/icon-reduce) + 日均关注文本
    .hits > .hits-number (总关注数)

特色：
- 提供 popularity_score（日均关注人次）替代 stars
- 提供 popularity_change（变化百分比）用于趋势显示
- 覆盖国内热门AI工具（豆包、Kimi、WorkBuddy、Trae等）
"""
import re
import logging
from typing import List, Dict, Any

from bs4 import BeautifulSoup

from .base import BaseCollector

logger = logging.getLogger(__name__)

# AIWW分类 → 百宝箱一级分类映射
CATEGORY_MAP = {
    "zhushou": "文本生成",
    "biancheng": "代码开发",
    "gongzuozhushou": "办公效率",
    "shipinshengcheng": "音视频",
    "sheji": "设计创意",
    "bangong": "办公效率",
    "xuexi": "教育培训",
    "xiezuo": "文本生成",
    "yinpin": "音视频",
    "tuwen": "图像创作",
    "yingxiao": "营销推广",
    "fanyi": "文本生成",
    "kefu": "办公效率",
    "jianmo": "图像创作",
    "huatu": "图像创作",
    "bianchengxuexi": "教育培训",
    "souhu": "文本生成",
    "liaotian": "文本生成",
    "yuancheng": "办公效率",
    "jiankong": "开发工具",
}


def parse_chinese_number(text: str) -> int:
    """解析中文数字格式（如"185.3万"、"7.9万"、"6857"）"""
    if not text:
        return 0
    text = text.strip().replace(",", "").replace(" ", "")
    if "万" in text:
        try:
            return int(float(text.replace("万", "")) * 10000)
        except (ValueError, TypeError):
            return 0
    if "亿" in text:
        try:
            return int(float(text.replace("亿", "")) * 100000000)
        except (ValueError, TypeError):
            return 0
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return 0


class Collector(BaseCollector):
    """AIWW.com 采集器"""

    def collect(self) -> List[Dict[str, Any]]:
        """采集AIWW工具列表"""
        items = []
        base_url = self.config.get("url", "https://www.aiww.com")

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

        # 1. 先采集各分类页面（确保工具有正确分类）
        categories_to_fetch = [
            "zhushou", "biancheng", "gongzuozhushou", "shipinshengcheng",
            "sheji", "bangong", "xuexi", "xiezuo", "yinpin", "tuwen",
        ]
        for cat in categories_to_fetch:
            try:
                resp = self.fetch(f"{base_url}/aitoplist/{cat}")
                soup = BeautifulSoup(resp.text, "html.parser")
                found = self._parse_ranking_page(soup, base_url, cat)
                items.extend(found)
                logger.info(f"[{self.source_id}] 分类 {cat}: {len(found)} 个工具")
            except Exception as e:
                logger.warning(f"[{self.source_id}] 采集分类 {cat} 失败: {e}")

        # 2. 再采集完整榜单 top20（补充分类页面未覆盖的工具）
        try:
            resp = self.fetch(f"{base_url}/aitoplist/all")
            soup = BeautifulSoup(resp.text, "html.parser")
            found = self._parse_ranking_page(soup, base_url, "all")
            items.extend(found)
            logger.info(f"[{self.source_id}] 完整榜单: {len(found)} 个工具")
        except Exception as e:
            logger.warning(f"[{self.source_id}] 采集完整榜单失败: {e}")

        items = self.dedup_by_url(items)
        logger.info(f"[{self.source_id}] 总计: {len(items)} 个工具（去重后）")
        return items

    def _parse_ranking_page(self, soup: BeautifulSoup, base_url: str, category: str) -> List[Dict]:
        """解析排行榜页面 - 基于实际HTML结构"""
        items = []
        mapped_category = CATEGORY_MAP.get(category, "其他")

        # 查找所有排名项: <li class="item rank-N">
        rank_items = soup.select("li.item[class*='rank-']")
        
        if not rank_items:
            logger.warning(f"[{self.source_id}] 未找到排名项 (category={category})")
            return items

        logger.debug(f"[{self.source_id}] 找到 {len(rank_items)} 个排名项")

        for li in rank_items:
            try:
                # === 排名 ===
                rank = 0
                rank_el = li.select_one(".rank .num")
                if rank_el:
                    try:
                        rank = int(rank_el.get_text(strip=True))
                    except ValueError:
                        pass

                # === 排名变化（从.change获取） ===
                rank_change_positions = 0
                change_el = li.select_one(".rank .change")
                if change_el:
                    change_text = change_el.get_text(strip=True)
                    if change_text and change_text != "-":
                        try:
                            rank_change_positions = int(change_text)
                        except ValueError:
                            pass

                # === 工具名和URL ===
                name_el = li.select_one("a.tt")
                if not name_el:
                    continue
                
                tool_name = name_el.get_text(strip=True)
                if not tool_name or len(tool_name) < 2:
                    continue

                href = name_el.get("href", "")
                slug = ""
                slug_match = re.search(r'/aitool/([a-z0-9]+)', href)
                if slug_match:
                    slug = slug_match.group(1)
                else:
                    continue

                # === 公司名 ===
                company = ""
                org_el = li.select_one(".organization")
                if org_el:
                    company = org_el.get_text(strip=True)

                # === 描述 ===
                description = ""
                desc_el = li.select_one(".info-desc p")
                if desc_el:
                    description = desc_el.get_text(strip=True)

                # === 图标URL ===
                icon_url = ""
                img_el = li.select_one("a.img-box img")
                if img_el:
                    icon_url = img_el.get("src", "")

                # === 日均关注人次 ===
                daily_visits = 0
                num_change_el = li.select_one(".num-change")
                if num_change_el:
                    # 文本中包含数字，如 "185.3万"
                    num_text = num_change_el.get_text(strip=True)
                    daily_visits = parse_chinese_number(num_text)

                # === 变化趋势方向 ===
                change_direction = 0  # 0=持平, 1=上升, -1=下降
                icon_el = li.select_one(".num-change i.iconfont")
                if icon_el:
                    icon_class = " ".join(icon_el.get("class", []))
                    if "icon-increase" in icon_class:
                        change_direction = 1
                    elif "icon-reduce" in icon_class:
                        change_direction = -1

                # === 总关注数 ===
                total_visits = 0
                hits_el = li.select_one(".hits-number")
                if hits_el:
                    try:
                        total_visits = int(hits_el.get_text(strip=True).replace(",", ""))
                    except ValueError:
                        pass

                # === 计算变化百分比 ===
                # 使用日均关注趋势方向（icon-increase/icon-reduce）
                # AIWW不直接提供百分比，根据方向给出合理估值
                change_percent = 0.0
                if change_direction == 1:
                    # 关注度上升：排名变化越大说明增长越猛
                    if rank_change_positions > 0:
                        change_percent = min(rank_change_positions * 10.0, 50.0)
                    else:
                        change_percent = 5.0  # 默认上升
                elif change_direction == -1:
                    # 关注度下降
                    if rank_change_positions > 0:
                        change_percent = -min(rank_change_positions * 10.0, 50.0)
                    else:
                        change_percent = -5.0  # 默认下降

                # === 构建工具URL ===
                tool_url = f"{base_url}/aitool/{slug}"

                items.append({
                    "name": tool_name,
                    "url": tool_url,
                    "description": description[:300],
                    "source": self.source_id,
                    "source_url": f"{base_url}/aitoplist/{category}",
                    "platform": ["aiww"],
                    "type": "ai_tool",
                    "is_china_tool": True,
                    "category": mapped_category if category != "all" else "其他",
                    "popularity_score": daily_visits,
                    "popularity_change": change_percent,
                    "raw_data": {
                        "rank": rank,
                        "rank_change_positions": rank_change_positions,
                        "change_direction": change_direction,
                        "company": company,
                        "total_visits": total_visits,
                        "daily_visits": daily_visits,
                        "slug": slug,
                        "aiww_url": tool_url,
                        "icon_url": icon_url,
                        "aiww_category": category,
                    },
                })

            except Exception as e:
                logger.debug(f"[{self.source_id}] 解析排名项失败: {e}")
                continue

        return items
