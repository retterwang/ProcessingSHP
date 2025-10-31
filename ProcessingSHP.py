"""
ProcessingSHP PyQt6 版本
楼宇库SHP文件处理工具 - 现代化GUI界面

特性：
- 现代化UI界面，支持深色主题
- 实时进度显示和详细日志输出
- 多文件处理和结果累积
- 预览功能展示处理结果
"""

import sys
import os
import re
import time
import threading
import queue
import multiprocessing
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QProgressBar, QPushButton, QTextEdit, QLabel, QFileDialog,
    QDialog, QInputDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFrame
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QThread, QTimer, QSize
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCursor, QIcon
)


# ============================================================================
# 主题检测函数
# ============================================================================

def get_system_theme():
    """检测系统使用的是深色或浅色主题"""
    try:
        import winreg
        # 检查 Windows 注册表中的主题设置
        registry_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            # value == 1: 浅色主题，value == 0: 深色主题
            return "light" if value == 1 else "dark"
    except Exception:
        # 如果无法读取注册表，尝试通过 Qt 调色板推断
        try:
            from PyQt6.QtWidgets import QApplication
            palette = QApplication.palette()
            # 使用背景色的亮度来判断
            bg_color = palette.color(palette.ColorRole.Window)
            # RGB 亮度计算
            brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
            return "light" if brightness > 128 else "dark"
        except Exception:
            return "light"  # 默认浅色主题


# ============================================================================
# 数据处理逻辑（复用Tkinter版本的业务代码）
# ============================================================================

# 城市名称到行政区编码的映射表
CITY_CODE_MAPPING = {
    # 北京市（直辖市）
    "Beijing": "110100",
    "北京": "110100",
    # 天津市（直辖市）
    "Tianjin": "120100",
    "天津": "120100",
    # 上海市（直辖市）
    "Shanghai": "310100",
    "上海": "310100",
    # 重庆市（直辖市）
    "Chongqing": "500100",
    "重庆": "500100",
    # 山西省
    "Taiyuan": "140100",       # 太原市
    "Datong": "140200",        # 大同市
    "Yangquan": "140300",      # 阳泉市
    "Changzhi": "140400",      # 长治市
    "Jincheng": "140500",      # 晋城市
    "Shuozhou": "140600",      # 朔州市
    "Jinzhong": "140700",      # 晋中市
    "Yuncheng": "140800",      # 运城市
    "Xinzhou": "140900",       # 忻州市
    "Linfen": "141000",        # 临汾市
    "Luliang": "141100",       # 吕梁市
    # 江苏省
    "Nanjing": "320100",       # 南京市
    "Wuxi": "320200",          # 无锡市
    "Xuzhou": "320300",        # 徐州市
    "Changzhou": "320400",     # 常州市
    "Suzhou": "320500",        # 苏州市
    "Nantong": "320600",       # 南通市
    "Lianyungang": "320700",   # 连云港市
    "Huai'an": "320800",       # 淮安市
    "Yancheng": "320900",      # 盐城市
    "Yangzhou": "321000",      # 扬州市
    "Zhenjiang": "321100",     # 镇江市
    "Taizhou": "321200",       # 泰州市
    "Suqian": "321300",        # 宿迁市
    # 安徽省
    "Hefei": "340100",         # 合肥市
    "Bengbu": "340300",        # 蚌埠市
    "Huainan": "340400",       # 淮南市
    "Maanshan": "340500",      # 马鞍山市
    "Huaibei": "340600",       # 淮北市
    "Tongling": "340700",      # 铜陵市
    "Anqing": "340800",        # 安庆市
    "Huangshan": "341000",     # 黄山市
    "Chuzhou": "341100",       # 滁州市
    "Fuyang": "341200",        # 阜阳市
    "Suzhou": "341300",        # 宿州市
    "Liuan": "341500",         # 六安市
    "Bozhou": "341600",        # 亳州市
    "Chizhou": "341700",       # 池州市
    "Xuancheng": "341800",     # 宣城市
    # 山东省
    "Jinan": "370100",         # 济南市
    "Qingdao": "370200",       # 青岛市
    "Zibo": "370300",          # 淄博市
    "Zaozhuang": "370400",     # 枣庄市
    "Dongying": "370500",      # 东营市
    "Yantai": "370600",        # 烟台市
    "Weifang": "370700",       # 潍坊市
    "Jining": "370800",        # 济宁市
    "Taian": "370900",         # 泰安市
    "Weihai": "371000",        # 威海市
    "Rizhao": "371100",        # 日照市
    "Laiwu": "371200",         # 莱芜市（历史代码，已并入济南）
    "Linyi": "371300",         # 临沂市
    "Dezhou": "371400",        # 德州市
    "Liaocheng": "371500",     # 聊城市
    "Binzhou": "371600",       # 滨州市
    "Heze": "371700",          # 菏泽市
    # 广东省
    "Guangzhou": "440100",     # 广州市
    "Shenzhen": "440300",      # 深圳市
    "Zhuhai": "440400",        # 珠海市
    "Shantou": "440500",       # 汕头市
    "Foshan": "440600",        # 佛山市
    "Shaoguan": "440200",      # 韶关市
    "Zhanjiang": "440800",     # 湛江市
    "Maoming": "440900",       # 茂名市
    "Jiangmen": "440700",      # 江门市
    "Zhaoqing": "441200",      # 肇庆市
    "Huizhou": "441300",       # 惠州市
    "Meizhou": "441400",       # 梅州市
    "Shanwei": "441500",       # 汕尾市
    "Heyuan": "441600",        # 河源市
    "Yangjiang": "441700",     # 阳江市
    "Qingyuan": "441800",      # 清远市
    "Dongguan": "441900",      # 东莞市
    "Zhongshan": "442000",     # 中山市
    "Chaozhou": "445100",      # 潮州市
    "Jieyang": "445200",       # 揭阳市
    "Yunfu": "445300",         # 云浮市
    # 广西壮族自治区
    "Nanning": "450100",       # 南宁市
    "Liuzhou": "450200",       # 柳州市
    "Guilin": "450300",        # 桂林市
    "Wuzhou": "450400",        # 梧州市
    "Beihai": "450500",        # 北海市
    "Fangchenggang": "450600", # 防城港市
    "Qinzhou": "450700",       # 钦州市
    "Guigang": "450800",       # 贵港市
    "Yulin": "450900",         # 玉林市
    "Baise": "451000",         # 百色市
    "Hezhou": "451100",        # 贺州市
    "Hechi": "451200",         # 河池市
    "Laibin": "451300",        # 来宾市
    "Chongzuo": "451400",      # 崇左市
    # 云南省
    "Kunming": "530100",       # 昆明市
    "昆明": "530100",
    "Qujing": "530300",        # 曲靖市
    "曲靖": "530300",
    "Yuxi": "530400",          # 玉溪市
    "玉溪": "530400",
    "Baoshan": "530500",       # 保山市
    "保山": "530500",
    "Zhaotong": "530600",      # 昭通市
    "昭通": "530600",
    "Lijiang": "530700",       # 丽江市
    "丽江": "530700",
    "Puer": "530800",          # 普洱市
    "普洱": "530800",
    "Lincang": "530900",       # 临沧市
    "临沧": "530900",
    "Chuxiong": "532300",      # 楚雄彝族自治州
    "楚雄": "532300",
    "Honghe": "532500",        # 红河哈尼族彝族自治州
    "红河": "532500",
    "Wenshan": "532600",       # 文山壮族苗族自治州
    "文山": "532600",
    "Xishuangbanna": "532800", # 西双版纳傣族自治州
    "西双版纳": "532800",
    "Dali": "532900",          # 大理白族自治州
    "大理": "532900",
    "Dehong": "533100",        # 德宏傣族景颇族自治州
    "德宏": "533100",
    "Nujiang": "533300",       # 怒江傈僳族自治州
    "怒江": "533300",
    "Diqing": "533400",        # 迪庆藏族自治州
    "迪庆": "533400",
    # 西藏自治区
    "Lasa": "540100",          # 拉萨市
    "Shigatse": "540200",      # 日喀则市
    "Shannan": "540500",       # 山南市
    "Linzhi": "540400",        # 林芝市
    "Naqu": "540600",          # 那曲市
    "Ali": "542500",           # 阿里地区
    # 陕西省
    "Xian": "610100",          # 西安市
    "Tongchuan": "610200",     # 铜川市（原“Tanyang”修正为正确拼音）
    "Baoji": "610300",         # 宝鸡市
    "Xianyang": "610400",      # 咸阳市
    "Weinan": "610500",        # 渭南市
    "Yanan": "610600",         # 延安市
    "Hanzhong": "610700",      # 汉中市
    "Yulin": "610800",         # 榆林市
    "Ankang": "610900",        # 安康市
    "Shangluo": "611000",      # 商洛市
    # 甘肃省
    "Lanzhou": "620100",       # 兰州市
    "Jiayuguan": "620200",     # 嘉峪关市
    "Jinchang": "620300",      # 金昌市
    "Baiyin": "620400",        # 白银市
    "Tianshui": "620500",      # 天水市
    "Wuwei": "620600",         # 武威市
    "Zhangye": "620700",       # 张掖市
    "Pingliang": "620800",     # 平凉市
    "Qingyang": "621000",      # 庆阳市
    "Dingxi": "621100",        # 定西市
    "Longnan": "621200",       # 陇南市
    "Gannan": "623000",        # 甘南藏族自治州
    "Linxia": "622900",        # 临夏回族自治州（剔除重复错误项）
    # 青海省
    "Xining": "630100",        # 西宁市
    "Haidong": "630200",       # 海东市
    "Haibei": "632200",        # 海北藏族自治州
    "Huangnan": "632300",      # 黄南藏族自治州
    "Hainan": "632500",        # 海南藏族自治州
    "Guoluo": "632600",        # 果洛藏族自治州（原“果洛”拼音修正为标准“Guoluo”）
    "Yushu": "632700",         # 玉树藏族自治州
    "Haixi": "632800",         # 海西蒙古族藏族自治州
    # 宁夏回族自治区
    "Yinchuan": "640100",      # 银川市
    "Shizuishan": "640200",    # 石嘴山市
    "Wuzhong": "640300",       # 吴忠市
    "Guyuan": "640400",        # 固原市
    "Zhongwei": "640500",      # 中卫市
    # 新疆维吾尔自治区
    "Urumqi": "650100",        # 乌鲁木齐市
    "Kelamayi": "650200",      # 克拉玛依市
    "Turpan": "650400",        # 吐鲁番市
    "Hami": "650500",          # 哈密市
    "Shihezi": "659001",       # 石河子市（省直辖县级市）
    "Alaer": "659002",         # 阿拉尔市（省直辖县级市，原“阿拉尔”拼音修正为“Alaer”）
    "Tumushuke": "659003",     # 图木舒克市（省直辖县级市）
    "Changji": "652300",       # 昌吉回族自治州
    "Bayinguoleng": "652800",  # 巴音郭楞蒙古自治州
    "Aksu": "652900",          # 阿克苏地区
    "Kashi": "653100",         # 喀什地区
    "Hetian": "653200",        # 和田地区
    "Kezhou": "653000",        # 克孜勒苏柯尔克孜自治州
    "Yili": "654000",          # 伊犁哈萨克自治州
    "Tacheng": "654200",       # 塔城地区
    "Altay": "654300"         # 阿勒泰地区（剔除县级市“库车”非地级项）
}


def _read_shp_to_pickle_worker(shp_path: str, out_pickle: str, rq: multiprocessing.Queue):
    """模块级多进程工作函数，用于读取shapefile"""
    try:
        import geopandas as _gpd
        gdf_local = _gpd.read_file(shp_path)
        gdf_local.to_pickle(out_pickle)
        try:
            rq.put((True, 'ok'))
        except Exception:
            pass
    except Exception as e:
        try:
            rq.put((False, str(e)))
        except Exception:
            pass


def get_city_code(city_name: str) -> Optional[str]:
    """根据城市名称获取行政区编码"""
    if not city_name:
        return None
    
    # 直接匹配（完全相同）
    if city_name in CITY_CODE_MAPPING:
        return CITY_CODE_MAPPING[city_name]
    
    # 清理城市名称（保持原始大小写用于首字母大写匹配）
    cleaned_name = re.sub(r'[^\w\u4e00-\u9fff]', '', city_name)
    
    # 尝试首字母大写匹配（对应映射表格式）
    title_case_name = cleaned_name.title() if cleaned_name else None
    if title_case_name and title_case_name in CITY_CODE_MAPPING:
        return CITY_CODE_MAPPING[title_case_name]
    
    # 小写匹配（备选）
    lower_name = cleaned_name.lower()
    if lower_name in CITY_CODE_MAPPING:
        return CITY_CODE_MAPPING[lower_name]
    
    # 尝试去除常见中文后缀
    for suffix in ['市', '区', '州', '县']:
        if cleaned_name.endswith(suffix):
            shortened = cleaned_name[:-len(suffix)]
            title_shortened = shortened.title()
            if title_shortened in CITY_CODE_MAPPING:
                return CITY_CODE_MAPPING[title_shortened]
    
    # 尝试去除常见英文后缀
    for suffix in ['shi', 'city', 'qu', 'district']:
        if lower_name.endswith(suffix):
            shortened = lower_name[:-len(suffix)]
            title_shortened = shortened.title()
            if title_shortened in CITY_CODE_MAPPING:
                return CITY_CODE_MAPPING[title_shortened]
    
    # 模糊匹配（首字母大写）
    for key in CITY_CODE_MAPPING:
        if key.lower() in lower_name or lower_name in key.lower():
            return CITY_CODE_MAPPING[key]
    
    return None


def process_shapefile(
    shp_file_path: str,
    progress_callback,
    city_id: Optional[str] = None
) -> Tuple[bool, str, Optional[pd.DataFrame]]:
    """
    处理shapefile文件的核心逻辑
    
    Args:
        shp_file_path: shapefile路径
        progress_callback: 进度回调函数 (progress_value, message)
        city_id: 城市编码（如果为None则自动识别或询问）
    
    Returns:
        (success, csv_path, result_df)
    """
    try:
        # ===== 1. 准备 =====
        progress_callback(5, "准备文件...")
        file_dir = os.path.dirname(shp_file_path)
        original_file_name = os.path.splitext(os.path.basename(shp_file_path))[0]
        csv_file_path = os.path.join(file_dir, f"{original_file_name}_final.csv")
        
        # ===== 2. 读取shapefile（使用子进程避免阻塞） =====
        progress_callback(10, "正在后台读取 Shapefile...")
        tmp_dir = tempfile.gettempdir()
        tmp_pickle = os.path.join(tmp_dir, f"{original_file_name}_tmp.pkl")
        result_q = multiprocessing.Queue()
        
        proc = multiprocessing.Process(
            target=_read_shp_to_pickle_worker,
            args=(shp_file_path, tmp_pickle, result_q)
        )
        proc.start()
        
        # 等待子进程完成，更新进度条
        progress_pct = 10
        while proc.is_alive():
            progress_pct = min(progress_pct + 1, 24)
            progress_callback(progress_pct, "")  # 空消息只更新进度条
            time.sleep(0.2)
        
        proc.join()
        success, msg = (False, 'unknown')
        try:
            if not result_q.empty():
                success, msg = result_q.get_nowait()
        except Exception:
            pass
        
        if not success:
            return False, f"读取失败: {msg}", None
        
        # 加载pickle
        try:
            gdf = pd.read_pickle(tmp_pickle)
        except Exception as e:
            return False, f"加载数据失败: {str(e)}", None
        finally:
            try:
                if os.path.exists(tmp_pickle):
                    os.remove(tmp_pickle)
            except Exception:
                pass
        
        original_count = len(gdf)
        progress_callback(25, f"读取完成 - {original_count} 个要素")
        
        # ===== 3. 修正几何 =====
        progress_callback(28, "修正几何图形...")
        if not gdf.geometry.is_valid.all():
            gdf['geometry'] = gdf.geometry.buffer(0)
            invalid_mask = ~gdf.geometry.is_valid
            invalid_count = invalid_mask.sum()
            if invalid_count > 0:
                gdf = gdf[~invalid_mask]
        progress_callback(35, f"修正几何完成 {len(gdf)}/{original_count} 要素")
        
        # ===== 4. 多部件转单部件 =====
        progress_callback(38, "多部件转单部件...")
        gdf = gdf.explode(index_parts=False)
        progress_callback(45, f"多部件处理完成 {len(gdf)} 个要素")
        
        # ===== 5. 删除重复 =====
        progress_callback(48, "删除重复几何...")
        gdf['wkt'] = gdf.geometry.apply(lambda x: x.wkt)
        gdf = gdf.drop_duplicates(subset='wkt', keep='first').drop(columns='wkt')
        progress_callback(55, f"重复删除完成 {len(gdf)} 个要素")
        
        # ===== 6. 面积筛选 =====
        progress_callback(58, "面积筛选...")
        gdf['areacalc'] = gdf.geometry.area
        before_filter = len(gdf)
        gdf = gdf[gdf['areacalc'] >= 80]
        progress_callback(65, f"面积筛选完成 {len(gdf)} 个要素")
        
        # ===== 7. 城市编码 =====
        progress_callback(68, "获取城市编码...")
        if not city_id:
            city_id = get_city_code(original_file_name)
            if not city_id:
                return False, f"无法识别城市编码: {original_file_name}", None
        
        progress_callback(75, f"城市编码: {city_id}")
        
        # ===== 8. 边界处理 =====
        progress_callback(78, "处理边界信息...")
        
        def get_boundary_str(geom):
            coords = []
            if isinstance(geom, Point):
                coords.append(f"{geom.x:.6f}_{geom.y:.6f}")
            elif isinstance(geom, LineString):
                for pt in geom.coords:
                    try:
                        coords.append(f"{float(pt[0]):.6f}_{float(pt[1]):.6f}")
                    except Exception:
                        pass
            elif isinstance(geom, Polygon):
                for pt in geom.exterior.coords:
                    try:
                        coords.append(f"{float(pt[0]):.6f}_{float(pt[1]):.6f}")
                    except Exception:
                        pass
            return ";".join(coords)
        
        try:
            if getattr(gdf, 'crs', None) is not None:
                gdf_4326 = gdf.to_crs(epsg=4326)
            else:
                gdf_4326 = gdf.copy()
        except Exception:
            gdf_4326 = gdf.copy()
        
        gdf['boundaries'] = gdf_4326.geometry.apply(get_boundary_str)
        progress_callback(85, "边界处理完成")
        
        # ===== 9. 导出CSV =====
        progress_callback(90, "生成最终数据...")
        gdf = gdf.reset_index(drop=True)
        gdf['build_id'] = [f"202510{original_file_name}_{i+1}" for i in range(len(gdf))]
        
        result_df = pd.DataFrame()
        result_df['city_id'] = [str(city_id)] * len(gdf)
        result_df['areacalc'] = gdf['areacalc'].astype(str)
        result_df['boundaries'] = gdf['boundaries'].astype(str)
        result_df['build_id'] = gdf['build_id'].astype(str)
        
        result_df.to_csv(csv_file_path, index=False, encoding='utf-8')
        progress_callback(100, "处理完成！")
        
        return True, csv_file_path, result_df
    
    except Exception as e:
        return False, f"处理出错: {str(e)}", None


# ============================================================================
# PyQt6 工作线程
# ============================================================================

class ProcessWorker(QThread):
    """Shapefile处理工作线程"""
    
    # 定义信号
    progress_signal = pyqtSignal(int, str)  # (progress_value, message)
    finished_signal = pyqtSignal(bool, str, object)  # (success, message, result_df)
    ask_city_id_signal = pyqtSignal(str)  # (file_name)
    
    def __init__(self, shp_file_path: str, city_id: Optional[str] = None):
        super().__init__()
        self.shp_file_path = shp_file_path
        self.city_id = city_id
        self.stop_flag = False
    
    def run(self):
        """线程主函数"""
        def progress_callback(value: int, message: str):
            self.progress_signal.emit(value, message)
        
        success, msg, result_df = process_shapefile(
            self.shp_file_path,
            progress_callback,
            self.city_id
        )
        
        self.finished_signal.emit(success, msg, result_df)
    
    def stop(self):
        """停止线程"""
        self.stop_flag = True


# ============================================================================
# 预览窗口
# ============================================================================

class PreviewWindow(QDialog):
    """结果预览窗口"""
    
    def __init__(self, parent, data, title="预览"):
        super().__init__(parent)
        self.setWindowTitle(title)
        # ✓ 修改：动态计算窗口尺寸而非固定值
        self.data = data
        self.theme = get_system_theme()  # 检测系统主题
        self.init_ui(data)
        self.adjust_window_size()
    
    def adjust_window_size(self):
        """根据内容调整窗口尺寸"""
        # 计算表格的合理宽度
        screen_geometry = self.screen().availableGeometry()
        max_width = int(screen_geometry.width() * 0.9)  # 屏幕宽度的 90%
        max_height = int(screen_geometry.height() * 0.85)  # 屏幕高度的 85%
        
        # 确定合理的窗口大小
        width = min(1200, max_width)
        height = min(700, max_height)
        
        self.setGeometry(100, 100, width, height)
    
    def init_ui(self, data):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # ✓ 修改：改进标题样式（提高对比度）
        title_label = QLabel(self.windowTitle())
        title_font = QFont('Microsoft YaHei', 12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1565C0; background-color: transparent;")
        layout.addWidget(title_label)
        
        # 数据展示区域使用滚动
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(15)
        
        # ✓ 修改：根据主题应用背景色
        if self.theme == "dark":
            scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #1e1e1e;
                    border: 1px solid #444;
                }
                QWidget {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                }
            """)
            scroll_content.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0;")
        
        # 数据展示
        if isinstance(data, list):
            # 多个DataFrame
            for file_name, df in data:
                self.add_dataframe_section(content_layout, file_name, df)
        else:
            # 单个DataFrame
            self.add_dataframe_section(content_layout, "处理结果数据", data)
        
        content_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setMinimumWidth(80)
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_dataframe_section(self, layout, title, df):
        """添加DataFrame展示区域"""
        # ✓ 修改：改进标题颜色对比度和样式
        section_title = QLabel(f"【{title}】- 前 {min(10, len(df))} 行（共 {len(df)} 行）")
        section_title.setStyleSheet(
            "font-weight: bold; color: #FFFFFF; background-color: #2196F3; "
            "padding: 8px; border-radius: 3px; margin: 5px 0px;"
        )
        section_title_font = QFont('Microsoft YaHei', 10)
        section_title_font.setBold(True)
        section_title.setFont(section_title_font)
        layout.addWidget(section_title)
        
        # 表格
        table = QTableWidget()
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)
        
        # 显示前10行
        preview_df = df.head(10)
        table.setRowCount(len(preview_df))
        
        for row_idx, (_, row) in enumerate(preview_df.iterrows()):
            for col_idx, col_name in enumerate(df.columns):
                item = QTableWidgetItem(str(row[col_name])[:100])
                item.setFont(QFont('Courier New', 9))
                table.setItem(row_idx, col_idx, item)
        
        # 调整列宽和表格外观
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # ✓ 修改：根据主题应用不同的样式
        if self.theme == "dark":
            # 深色主题样式
            table.setStyleSheet("""
                QTableWidget {
                    border: 1px solid #444;
                    border-radius: 4px;
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                }
                QTableWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #3d3d3d;
                    color: #e0e0e0;
                    background-color: #2b2b2b;
                }
                QTableWidget::item:selected {
                    background-color: #1565C0;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #1565C0;
                    color: #ffffff;
                    padding: 6px;
                    border: none;
                    border-bottom: 2px solid #0d47a1;
                    font-weight: bold;
                }
                QHeaderView::section:hover {
                    background-color: #1976D2;
                }
                QTableWidget::horizontalHeader {
                    background-color: #1565C0;
                }
                QTableWidget::verticalHeader {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                }
            """)
        else:
            # 浅色主题样式（保持原样）
            table.setStyleSheet("""
                QTableWidget {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: white;
                }
                QTableWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #eee;
                }
                QHeaderView::section {
                    background-color: #f5f5f5;
                    color: #333;
                    padding: 6px;
                    border: none;
                    border-bottom: 2px solid #2196F3;
                    font-weight: bold;
                }
                QHeaderView::section:hover {
                    background-color: #e8e8e8;
                }
            """)
        
        # 计算合理高度（每行约 25-30 像素）
        row_height = table.verticalHeader().defaultSectionSize()
        table_height = (len(preview_df) + 1) * row_height + 5
        table.setMinimumHeight(min(table_height, 350))
        table.setMaximumHeight(450)
        
        layout.addWidget(table)


# ============================================================================
# 主窗口
# ============================================================================

class MainWindow(QMainWindow):
    """主应用窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("楼宇库处理程序 v2.3")
        
        # 严格的大小控制 - 防止任何自动调整
        self.setFixedSize(520, 650)  # 使用固定大小而不是最小/最大
        self.move(100, 100)  # 明确设置位置
        
        # 检测系统主题
        self.theme = get_system_theme()
        
        # 数据存储
        self.all_results: List[Tuple[str, pd.DataFrame]] = []
        self.current_worker: Optional[ProcessWorker] = None
        self.current_shp_file: Optional[str] = None
        
        # 初始化UI
        self.init_ui()
        
        # 应用样式
        self.apply_stylesheet()
    # 固定尺寸已在上方设置，无需再次调整
    
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 使用较小的间距和边距
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # ===== 欢迎区域 - 紧凑设计 =====
        welcome_label = QLabel(
            "欢迎使用楼宇库数据处理工具 v2.3\n"
            "本工具将SHP文件转换为CSV格式"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_font = QFont('Microsoft YaHei', 9)  # 缩小到9pt
        welcome_label.setFont(welcome_font)
        
        if self.theme == "dark":
            welcome_label.setStyleSheet("color: #a0a0a0; margin: 0px; padding: 2px;")
        else:
            welcome_label.setStyleSheet("color: #666; margin: 0px; padding: 2px;")
        layout.addWidget(welcome_label)
        
        # ===== 进度条 - 保持紧凑 =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setMaximumHeight(20)
        
        if self.theme == "dark":
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #444;
                    border-radius: 3px;
                    background-color: #1e1e1e;
                    text-align: center;
                    color: #e0e0e0;
                    font-size: 8pt;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 2px;
                }
            """)
        else:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    background-color: #f0f0f0;
                    text-align: center;
                    color: #333;
                    font-size: 8pt;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 2px;
                }
            """)
        layout.addWidget(self.progress_bar)
        
        # ===== 日志显示区 =====
        log_label = QLabel("处理日志")
        log_label.setFont(QFont('Microsoft YaHei', 8, weight=QFont.Weight.Bold))
        log_label.setStyleSheet("margin: 0px; padding: 0px;")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier New', 8))
        # 让日志区成为主要的可伸缩区域：更小的最小高度 + 不限制最大高度
        self.log_text.setMinimumHeight(140)
        if self.theme == "dark":
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #2b2b2b;
                    border: 1px solid #444;
                    border-radius: 2px;
                    padding: 4px;
                    color: #e0e0e0;
                    margin: 0px;
                }
            """)
        else:
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 2px;
                    padding: 4px;
                    color: #333;
                    margin: 0px;
                }
            """)
        # 将剩余空间分配给日志区域
        layout.addWidget(self.log_text, 1)

        # ===== 底部按钮区域（容器，固定高度，行间距合理） =====
        buttons_container = QWidget()
        buttons_layout = QVBoxLayout(buttons_container)
        buttons_layout.setSpacing(8)
        buttons_layout.setContentsMargins(0, 8, 0, 0)  # 与日志区拉开距离

        # 第一行：选择文件 + 预览结果
        button_row1 = QHBoxLayout()
        button_row1.setSpacing(8)
        button_row1.setContentsMargins(0, 0, 0, 0)

        self.select_file_btn = QPushButton("选择 SHP 文件")
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_file_btn.setMinimumHeight(32)
        self.select_file_btn.setMaximumHeight(32)
        self.select_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 2px;
                font-weight: bold;
                font-size: 9pt;
                padding: 0px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:pressed { background-color: #1565C0; }
            QPushButton:disabled { background-color: #bbb; color: #777; }
        """)
        button_row1.addWidget(self.select_file_btn)

        self.preview_btn = QPushButton("预览结果")
        self.preview_btn.clicked.connect(self.show_preview)
        self.preview_btn.setMinimumHeight(32)
        self.preview_btn.setMaximumHeight(32)
        self.preview_btn.setEnabled(False)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 2px;
                font-weight: bold;
                font-size: 9pt;
                padding: 0px;
            }
            QPushButton:hover { background-color: #F57C00; }
            QPushButton:pressed { background-color: #E65100; }
            QPushButton:disabled { background-color: #bbb; color: #777; }
        """)
        button_row1.addWidget(self.preview_btn)
        buttons_layout.addLayout(button_row1)

        # 第二行：导出日志 + 清空结果
        button_row2 = QHBoxLayout()
        button_row2.setSpacing(8)
        button_row2.setContentsMargins(0, 0, 0, 0)

        self.export_log_btn = QPushButton("导出日志")
        self.export_log_btn.clicked.connect(self.export_log)
        self.export_log_btn.setMinimumHeight(32)
        self.export_log_btn.setMaximumHeight(32)
        self.export_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 2px;
                font-weight: bold;
                font-size: 9pt;
                padding: 0px;
            }
            QPushButton:hover { background-color: #388E3C; }
            QPushButton:pressed { background-color: #2E7D32; }
        """)
        button_row2.addWidget(self.export_log_btn)

        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.clicked.connect(self.clear_results)
        self.clear_btn.setMinimumHeight(32)
        self.clear_btn.setMaximumHeight(32)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 2px;
                font-weight: bold;
                font-size: 9pt;
                padding: 0px;
            }
            QPushButton:hover { background-color: #D32F2F; }
            QPushButton:pressed { background-color: #C62828; }
        """)
        button_row2.addWidget(self.clear_btn)
        buttons_layout.addLayout(button_row2)

        # 第三行：退出程序（占满宽度）
        self.exit_btn = QPushButton("退出程序")
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setMinimumHeight(32)
        self.exit_btn.setMaximumHeight(32)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 2px;
                font-weight: bold;
                font-size: 9pt;
                padding: 0px;
            }
            QPushButton:hover { background-color: #7B1FA2; }
            QPushButton:pressed { background-color: #6A1B9A; }
        """)
        buttons_layout.addWidget(self.exit_btn)

        layout.addWidget(buttons_container)

        central_widget.setLayout(layout)
    
    def apply_stylesheet(self):
        """应用全局样式表"""
        if self.theme == "dark":
            # 深色主题样式
            stylesheet = """
                QMainWindow {
                    background-color: #1e1e1e;
                }
                QLabel {
                    color: #e0e0e0;
                    background-color: transparent;
                }
                QTextEdit {
                    color: #e0e0e0;
                    background-color: #2b2b2b;
                    border: 1px solid #444;
                }
                QMessageBox {
                    background-color: #2b2b2b;
                }
                QMessageBox QLabel {
                    color: #e0e0e0;
                }
                QMessageBox QPushButton {
                    min-width: 50px;
                }
            """
        else:
            # 浅色主题样式
            stylesheet = """
                QMainWindow {
                    background-color: #fafafa;
                }
                QLabel {
                    color: #333;
                    background-color: transparent;
                }
                QTextEdit {
                    color: #333;
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                }
            """
        self.setStyleSheet(stylesheet)
    
    def select_file(self):
        """选择SHP文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Shapefile 文件",
            "",
            "Shapefile 文件 (*.shp);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        self.current_shp_file = file_path
        self.add_log(f"已选择文件: {os.path.basename(file_path)}")
        self.start_processing(file_path)
    
    def start_processing(self, file_path: str):
        """开始处理文件"""
        self.select_file_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        # ✓ 修改：不清空日志，改为追加分隔符
        self.add_log("\n" + "="*60)
        self.add_log(f"开始处理新文件: {os.path.basename(file_path)}")
        self.add_log("="*60)
        
        # 创建并启动工作线程
        self.current_worker = ProcessWorker(file_path)
        self.current_worker.progress_signal.connect(self.on_progress)
        self.current_worker.finished_signal.connect(self.on_finished)
        self.current_worker.start()
    
    def on_progress(self, value: int, message: str):
        """处理进度更新信号"""
        self.progress_bar.setValue(value)
        if message:  # 只在有消息时添加日志
            self.add_log(message)
    
    def on_finished(self, success: bool, message: str, result_df):
        """处理完成信号"""
        self.select_file_btn.setEnabled(True)
        
        if success:
            self.add_log("\n✓ 处理成功！")
            if result_df is not None:
                # 保存结果
                file_name = os.path.splitext(os.path.basename(self.current_shp_file))[0]
                self.all_results.append((file_name, result_df))
                self.preview_btn.setEnabled(True)
                
                # 显示统计信息
                self.add_log(f"保存行数: {len(result_df)}")
                self.add_log(f"已累积处理文件数: {len(self.all_results)}")
        else:
            self.add_log(f"\n✗ 处理失败: {message}")
            QMessageBox.critical(self, "错误", f"处理失败:\n{message}")
    
    def add_log(self, message: str):
        """添加日志消息"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if self.log_text.toPlainText():
            cursor.insertText("\n")
        
        cursor.insertText(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
    
    def show_preview(self):
        """显示预览窗口"""
        if not self.all_results:
            QMessageBox.warning(self, "提示", "没有可预览的数据")
            return
        
        # 根据结果数量选择显示方式
        if len(self.all_results) > 1:
            title = f"处理结果预览 (共 {len(self.all_results)} 个文件)"
            preview_window = PreviewWindow(self, self.all_results, title)
        else:
            file_name, df = self.all_results[0]
            title = f"处理结果预览: {file_name}"
            preview_window = PreviewWindow(self, df, title)
        
        preview_window.exec()
    
    def export_log(self):
        """导出日志"""
        log_text = self.log_text.toPlainText()
        if not log_text:
            QMessageBox.warning(self, "提示", "日志为空")
            return
        
        # 默认保存位置
        default_path = os.path.join(
            os.path.expanduser("~"),
            f"处理日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            default_path,
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(log_text)
            QMessageBox.information(self, "成功", f"日志已导出到:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")
    
    def clear_results(self):
        """清空结果"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清空所有结果吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.all_results.clear()
            self.log_text.clear()
            self.progress_bar.setValue(0)
            self.preview_btn.setEnabled(False)
            self.add_log("结果已清空")
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        if self.current_worker and self.current_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "确认退出",
                "处理还未完成，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            self.current_worker.stop()
            self.current_worker.wait()
        
        event.accept()


# ============================================================================
# 应用入口
# ============================================================================

def main():
    """应用主函数"""
    # 检查依赖
    required_packages = {
        'geopandas': 'pip install geopandas',
        'shapely': 'pip install shapely',
        'PyQt6': 'pip install PyQt6'
    }
    
    missing = []
    for package, install_cmd in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing.append(f"{package} ({install_cmd})")
    
    if missing:
        print("缺少以下依赖:")
        for pkg in missing:
            print(f"  - {pkg}")
        return
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # DEBUG: 打印窗口信息
    print(f"[OK] Window displayed")
    print(f"  Geometry: {window.geometry()}")
    print(f"  Size: {window.size()}")
    print(f"  Position: ({window.x()}, {window.y()})")
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
