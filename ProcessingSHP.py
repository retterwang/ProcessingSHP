import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import geopandas as gpd
import pandas as pd
import os
from shapely.geometry import Polygon, LineString, Point

def update_progress(progress_var, status_label, value, message):
    """更新进度条和状态信息（修正参数顺序）"""
    progress_var.set(value)
    status_label.config(text=message)
    status_label.update_idletasks()  # 强制刷新界面

def shp_to_csv_with_preprocessing():
    # 创建主进度窗口
    progress_window = tk.Toplevel()
    progress_window.title("处理进度")
    progress_window.geometry("500x150")
    progress_window.resizable(False, False)
    
    # 进度条
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(
        progress_window,
        variable=progress_var,
        length=450,
        mode='determinate'
    )
    progress_bar.pack(pady=20)
    
    # 状态标签
    status_label = tk.Label(progress_window, text="准备开始处理...", wraplength=450)
    status_label.pack(pady=10)
    
    # 初始化进度
    update_progress(progress_var, status_label, 0, "准备开始处理...")

    try:
        # 1. 选择shp文件
        update_progress(progress_var, status_label, 5, "请选择Shapefile文件...")
        shp_file_path = filedialog.askopenfilename(
            title="选择Shapefile文件",
            filetypes=[("Shapefile文件", "*.shp")]
        )
        
        if not shp_file_path:
            update_progress(progress_var, status_label, 0, "未选择文件，程序退出")
            messagebox.showinfo("提示", "未选择文件，程序退出")
            progress_window.destroy()
            return
        
        # 获取文件信息
        file_dir = os.path.dirname(shp_file_path)
        original_file_name = os.path.splitext(os.path.basename(shp_file_path))[0]
        csv_file_path = os.path.join(file_dir, f"{original_file_name}_final.csv")
        update_progress(progress_var, status_label, 10, f"已选择文件：{original_file_name}.shp")

        # 2. 读取shapefile
        update_progress(progress_var, status_label, 15, "正在读取Shapefile文件...")
        gdf = gpd.read_file(shp_file_path)
        original_count = len(gdf)
        update_progress(progress_var, status_label, 20, f"成功读取数据，共{original_count}个要素")

        # 3. 修正几何图形
        update_progress(progress_var, status_label, 25, "开始修正几何图形...")
        if not gdf.geometry.is_valid.all():
            gdf['geometry'] = gdf.geometry.buffer(0)
            invalid_mask = ~gdf.geometry.is_valid
            invalid_count = invalid_mask.sum()
            if invalid_count > 0:
                gdf = gdf[~invalid_mask]
                update_progress(progress_var, status_label, 35, 
                               f"修正几何完成，移除了{invalid_count}个无法修复的无效几何")
            else:
                update_progress(progress_var, status_label, 35, 
                               "几何图形修正完成，所有几何均有效")
        else:
            update_progress(progress_var, status_label, 35, "所有几何图形均有效，无需修正")

        # 4. 多部件转单部件
        update_progress(progress_var, status_label, 40, "开始将多部件转为单部件...")
        gdf = gdf.explode(index_parts=False)
        multi_part_count = len(gdf) - original_count
        update_progress(progress_var, status_label, 50, 
                       f"多部件转单部件完成，新增{multi_part_count}个单部件要素，当前共{len(gdf)}个要素")

        # 5. 删除重复几何
        update_progress(progress_var, status_label, 55, "开始删除重复几何图形...")
        gdf['wkt'] = gdf.geometry.apply(lambda x: x.wkt)
        gdf = gdf.drop_duplicates(subset='wkt', keep='first').drop(columns='wkt')
        duplicate_count = (original_count + multi_part_count) - len(gdf)
        update_progress(progress_var, status_label, 65, 
                       f"重复几何删除完成，移除了{duplicate_count}个重复要素，当前共{len(gdf)}个要素")

        # 6. 面积计算与筛选
        update_progress(progress_var, status_label, 70, "开始计算面积并筛选要素...")
        gdf['areacalc'] = gdf.geometry.area
        before_filter_count = len(gdf)
        gdf = gdf[gdf['areacalc'] >= 80]
        small_area_count = before_filter_count - len(gdf)
        update_progress(progress_var, status_label, 75, 
                       f"面积筛选完成，移除了{small_area_count}个面积小于80的要素，当前共{len(gdf)}个要素")

        # 7. 处理城市编码
        update_progress(progress_var, status_label, 80, "请输入城市编码...")
        city_id = simpledialog.askstring(
            "输入城市编码", 
            "请输入城市编码（字符串类型）：",
            parent=progress_window
        )
        if not city_id:
            update_progress(progress_var, status_label, 80, "未输入城市编码，程序退出")
            messagebox.showerror("错误", "未输入城市编码，程序退出")
            progress_window.destroy()
            return
        update_progress(progress_var, status_label, 85, f"已获取城市编码：{city_id}")

        # 8. 处理边界信息
        update_progress(progress_var, status_label, 85, "正在处理边界信息...")
        def get_boundary_str(geom):
            coords = []
            if isinstance(geom, Point):
                coords.append(f"{geom.x:.6f}_{geom.y:.6f}")
            elif isinstance(geom, LineString):
                points = list(geom.coords)
                coords = []
                for pt in points:
                    # pt may be (x, y) or (x, y, z); take first two components
                    try:
                        x = float(pt[0]); y = float(pt[1])
                        coords.append(f"{x:.6f}_{y:.6f}")
                    except Exception:
                        # skip invalid coordinate tuples
                        continue
            elif isinstance(geom, Polygon):
                points = list(geom.exterior.coords)
                coords = []
                for pt in points:
                    try:
                        x = float(pt[0]); y = float(pt[1])
                        coords.append(f"{x:.6f}_{y:.6f}")
                    except Exception:
                        continue
            return ";".join(coords)
        
        gdf['boundaries'] = gdf.geometry.apply(get_boundary_str)
        update_progress(progress_var, status_label, 90, "边界信息处理完成")

        # 9. 生成build_id并导出
        update_progress(progress_var, status_label, 90, "正在生成最终数据并导出...")
        gdf = gdf.reset_index(drop=True)
        gdf['build_id'] = [f"202510{original_file_name}_{i+1}" for i in range(len(gdf))]
        
        # 构建结果数据框
        result_df = pd.DataFrame()
        result_df['city_id'] = [str(city_id)] * len(gdf)
        result_df['areacalc'] = gdf['areacalc'].astype(str)
        result_df['boundaries'] = gdf['boundaries'].astype(str)
        result_df['build_id'] = gdf['build_id'].astype(str)
        
        # 导出CSV
        result_df.to_csv(csv_file_path, index=False, encoding='utf-8')
        update_progress(progress_var, status_label, 100, "所有处理已完成！")

        # 完成提示
        messagebox.showinfo("转换完成", 
                          f"所有处理完成！\n"
                          f"原始要素数：{original_count}\n"
                          f"最终保留要素数：{len(result_df)}\n"
                          f"CSV文件已保存至：\n{csv_file_path}")
        progress_window.destroy()

    except Exception as e:
        update_progress(progress_var, status_label, 0, f"处理出错：{str(e)}")
        messagebox.showerror("处理错误", f"处理过程中出现错误：\n{str(e)}")
        progress_window.destroy()

if __name__ == "__main__":
    # 主窗口（仅用于初始化Tkinter）
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 检查依赖库
    required_libs = {
        'geopandas': 'pip install geopandas',
        'shapely': 'pip install shapely'
    }
    missing_libs = []
    for lib, install_cmd in required_libs.items():
        try:
            __import__(lib)
        except ImportError:
            missing_libs.append(f"{lib}（安装命令：{install_cmd}）")
    
    if missing_libs:
        messagebox.showerror("缺少依赖库", 
                           "请先安装以下库：\n" + "\n".join(missing_libs))
        root.destroy()
        exit(1)
    
    # 开始处理
    shp_to_csv_with_preprocessing()
    root.destroy()