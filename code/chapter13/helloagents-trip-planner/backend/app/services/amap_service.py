"""高德地图MCP服务封装"""

import json
from typing import List, Dict, Any, Optional
from hello_agents.tools import MCPTool
from ..config import get_settings, get_amap_mcp_server_command
from ..models.schemas import Location, POIInfo, WeatherInfo

# 全局MCP工具实例
_amap_mcp_tool = None


def _extract_json(result: str) -> Dict[str, Any]:
    """从MCP工具返回的文本中提取JSON对象"""
    if not result:
        raise ValueError("MCP工具返回内容为空")

    start = result.find("{")
    end = result.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"无法从MCP返回内容中解析JSON: {result[:200]}")

    return json.loads(result[start:end + 1])


def _as_str(value: Any, default: str = "") -> str:
    """将高德返回的字符串/列表/空值统一转换为字符串"""
    if value is None:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "、".join(str(item) for item in value if item)
    if isinstance(value, dict):
        return "、".join(str(item) for item in value.values() if item)
    return str(value)


def _parse_location(value: Optional[str]) -> Optional[Location]:
    """解析高德坐标字符串 '经度,纬度'"""
    if not value or "," not in value:
        return None

    try:
        longitude, latitude = value.split(",", 1)
        return Location(longitude=float(longitude), latitude=float(latitude))
    except (TypeError, ValueError):
        return None


def get_amap_mcp_tool() -> MCPTool:
    """
    获取高德地图MCP工具实例(单例模式)

    Returns:
        MCPTool实例
    """
    global _amap_mcp_tool

    if _amap_mcp_tool is None:
        settings = get_settings()

        if not settings.amap_api_key:
            raise ValueError("高德地图API Key未配置,请在.env文件中设置AMAP_API_KEY")

        server_command = get_amap_mcp_server_command()

        # 创建MCP工具
        _amap_mcp_tool = MCPTool(
            name="amap",
            description="高德地图服务,支持POI搜索、路线规划、天气查询等功能",
            server_command=server_command,
            env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
            auto_expand=True  # 自动展开为独立工具
        )

        # 工具发现失败时MCPTool内部会静默忽略异常,这里必须显式报错,
        # 否则Agent只会看到未展开的工具并报"未找到工具"
        if not _amap_mcp_tool._available_tools:
            _amap_mcp_tool = None
            raise RuntimeError(
                "无法从高德地图MCP服务器获取工具列表。\n"
                f"  启动命令: {' '.join(server_command)}\n"
                "  请检查: 1) 已安装 Node.js (node/npx 可用); "
                "2) 网络可访问 npm registry; 3) AMAP_API_KEY 配置正确。"
            )

        print(f"✅ 高德地图MCP工具初始化成功")
        print(f"   工具数量: {len(_amap_mcp_tool._available_tools)}")
        print("   可用工具: " + ", ".join(
            tool.get("name", "unknown") for tool in _amap_mcp_tool._available_tools
        ))

    return _amap_mcp_tool


class AmapService:
    """高德地图服务封装类"""

    def __init__(self):
        """初始化服务"""
        self.mcp_tool = get_amap_mcp_tool()

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用MCP工具并返回原始文本"""
        return self.mcp_tool.run({
            "action": "call_tool",
            "tool_name": tool_name,
            "arguments": arguments
        })

    def search_poi(self, keywords: str, city: Optional[str] = None, citylimit: bool = True) -> List[POIInfo]:
        """
        搜索POI

        Args:
            keywords: 搜索关键词
            city: 城市
            citylimit: 是否限制在城市范围内(高德MCP文本搜索暂不支持该参数,保留以兼容调用方)

        Returns:
            POI信息列表
        """
        try:
            arguments = {"keywords": keywords}
            if city:
                arguments["city"] = city

            result = self._call_tool("maps_text_search", arguments)

            data = _extract_json(result)
            pois = []

            for poi in data.get("pois", []):
                photos = []
                photo_info = poi.get("photos")
                if isinstance(photo_info, dict):
                    if photo_info.get("url"):
                        photos.append(photo_info["url"])
                elif isinstance(photo_info, list):
                    photos = [p.get("url") for p in photo_info if isinstance(p, dict) and p.get("url")]

                pois.append(POIInfo(
                    id=_as_str(poi.get("id")),
                    name=_as_str(poi.get("name")),
                    type=_as_str(poi.get("typecode") or poi.get("type")),
                    address=_as_str(poi.get("address")),
                    location=_parse_location(poi.get("location")),
                    tel=_as_str(poi.get("tel")) or None,
                    photos=photos
                ))

            print(f"POI搜索成功: {len(pois)} 条结果")
            return pois

        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []

    def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        查询天气

        Args:
            city: 城市名称

        Returns:
            天气信息列表
        """
        try:
            result = self._call_tool("maps_weather", {"city": city})

            data = _extract_json(result)
            weather_list = []

            for forecast in data.get("forecasts", []):
                day_wind = forecast.get("daywind", "")
                night_wind = forecast.get("nightwind", "")
                day_power = forecast.get("daypower", "")
                night_power = forecast.get("nightpower", "")

                weather_list.append(WeatherInfo(
                    date=forecast.get("date", ""),
                    day_weather=forecast.get("dayweather", ""),
                    night_weather=forecast.get("nightweather", ""),
                    day_temp=forecast.get("daytemp", 0),
                    night_temp=forecast.get("nighttemp", 0),
                    wind_direction=f"{day_wind}/{night_wind}" if night_wind else day_wind,
                    wind_power=f"{day_power}/{night_power}" if night_power else day_power
                ))

            print(f"天气查询成功: {len(weather_list)} 天")
            return weather_list

        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking"
    ) -> Dict[str, Any]:
        """
        规划路线

        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_city: 起点城市
            destination_city: 终点城市
            route_type: 路线类型 (walking/driving/transit)

        Returns:
            路线信息
        """
        try:
            # 高德MCP路线规划工具使用坐标而非地址,先做地理编码
            origin = self.geocode(origin_address, origin_city)
            destination = self.geocode(destination_address, destination_city)

            if not origin or not destination:
                print("❌ 路线规划失败: 无法解析起点或终点坐标")
                return {}

            origin_str = f"{origin.longitude},{origin.latitude}"
            destination_str = f"{destination.longitude},{destination.latitude}"

            if route_type == "transit":
                tool_name = "maps_direction_transit_integrated"
                arguments = {
                    "origin": origin_str,
                    "destination": destination_str,
                    "city": origin_city or destination_city or "",
                    "cityd": destination_city or origin_city or ""
                }
            elif route_type == "driving":
                tool_name = "maps_direction_driving"
                arguments = {"origin": origin_str, "destination": destination_str}
            else:
                tool_name = "maps_direction_walking"
                arguments = {"origin": origin_str, "destination": destination_str}

            result = self._call_tool(tool_name, arguments)
            data = _extract_json(result)
            route = data.get("route", {})

            paths = route.get("paths") or []
            if paths:
                path = paths[0]
                steps = path.get("steps") or []
                description = " -> ".join(
                    step.get("instruction", "") for step in steps[:5] if step.get("instruction")
                )
                return {
                    "distance": float(path.get("distance", 0) or 0),
                    "duration": int(float(path.get("duration", 0) or 0)),
                    "route_type": route_type,
                    "description": description or "路线规划成功"
                }

            # 公共交通返回的是 transits 结构
            transits = route.get("transits") or []
            if transits:
                transit = transits[0]
                segments = transit.get("segments") or []
                description_parts = []
                for segment in segments:
                    bus = segment.get("bus", {}).get("buslines") or []
                    if bus:
                        description_parts.append(bus[0].get("name", ""))

                return {
                    "distance": float(transit.get("distance", 0) or transit.get("walking_distance", 0) or 0),
                    "duration": int(float(transit.get("duration", 0) or 0)),
                    "route_type": route_type,
                    "description": " -> ".join(p for p in description_parts if p) or "路线规划成功"
                }

            print("❌ 路线规划失败: 返回结果中没有可用路线")
            return {}

        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            return {}

    def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码(地址转坐标)

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
        """
        try:
            arguments = {"address": address}
            if city:
                arguments["city"] = city

            result = self._call_tool("maps_geo", arguments)
            data = _extract_json(result)

            geocodes = data.get("return") or data.get("geocodes") or []
            if geocodes:
                return _parse_location(geocodes[0].get("location"))

            print(f"❌ 地理编码失败: 未找到地址 '{address}' 的坐标")
            return None

        except Exception as e:
            print(f"❌ 地理编码失败: {str(e)}")
            return None

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        获取POI详情

        Args:
            poi_id: POI ID

        Returns:
            POI详情信息
        """
        try:
            result = self._call_tool("maps_search_detail", {"id": poi_id})

            data = _extract_json(result)
            print(f"POI详情获取成功: {data.get('name', poi_id)}")
            return data

        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {}


# 创建全局服务实例
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service

    if _amap_service is None:
        _amap_service = AmapService()

    return _amap_service
