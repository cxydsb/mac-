# -*- coding: utf-8 -*-
import os
import sys
import shutil
import subprocess

# 兼容 PySide2 与 PySide6
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

# ==========================================
# 配置常量与系统适配
# ==========================================
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.tga', '.exr'}

# 在用户的文档目录下创建一个主库文件夹
MAC_ASSET_ROOT = os.path.join(os.path.expanduser("~"), "Documents", "MacAssetLibrary").replace("\\", "/")

def open_with_mac_default(path):
    """苹果系统专属：用系统默认程序打开文件"""
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.call(["open", path])
        elif sys.platform == "win32": # 兼容性保留
            os.startfile(path)
        else:
            subprocess.call(["xdg-open", path])
    except Exception as e:
        print(f"打开失败: {e}")

# ==========================================
# UI 样式表 (极简 macOS 风格)
# ==========================================
MAC_STYLE_QSS = """
QWidget { 
    background-color: #1e1e1e; 
    color: #e0e0e0; 
    font-family: ".AppleSystemUIFont", "Helvetica Neue", sans-serif; 
    font-size: 13px; 
}
QListWidget { 
    background-color: #252526; 
    border: 1px solid #3c3c3c; 
    border-radius: 6px; 
    padding: 5px; 
    outline: none; 
}
QListWidget::item { 
    border-radius: 4px; 
    margin: 2px; 
}
QListWidget::item:hover { 
    background-color: #2a2d2e; 
}
QListWidget::item:selected { 
    background-color: #005f9e; 
    color: #ffffff; 
}
QLineEdit { 
    background-color: #3c3c3c; 
    border: 1px solid #555555; 
    border-radius: 4px; 
    padding: 6px; 
    color: #eeeeee; 
}
QLineEdit:focus { 
    border: 1px solid #007fd4; 
}
QPushButton { 
    background-color: #333333; 
    border: 1px solid #555555; 
    border-radius: 4px; 
    padding: 6px 12px; 
    color: #eeeeee; 
}
QPushButton:hover { 
    background-color: #444444; 
}
QPushButton:pressed { 
    background-color: #222222; 
}
QSplitter::handle { 
    background-color: #3c3c3c; 
    margin: 0px 2px; 
}
QScrollBar:vertical { 
    border: none; 
    background: #1e1e1e; 
    width: 10px; 
    margin: 0px; 
}
QScrollBar::handle:vertical { 
    background: #424242; 
    min-height: 20px; 
    border-radius: 5px; 
}
QScrollBar::handle:vertical:hover { 
    background: #4f4f4f; 
}
"""

# ==========================================
# 核心组件：支持拖拽导入的缩略图列表
# ==========================================
class AssetViewport(QtWidgets.QListWidget):
    files_dropped = QtCore.Signal(list)

    def __init__(self, parent=None):
        super(AssetViewport, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop) # 禁用内部乱序拖拽，专注外部导入
        
        # 网格视图设置
        self.setViewMode(QtWidgets.QListWidget.IconMode)
        self.setIconSize(QtCore.QSize(160, 160))
        self.setGridSize(QtCore.QSize(180, 200))
        self.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.setMovement(QtWidgets.QListWidget.Static)
        self.setWordWrap(True)
        self.setSpacing(10)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if urls:
                self.files_dropped.emit(urls)
            event.acceptProposedAction()
        else:
            event.ignore()

# ==========================================
# 主程序窗口
# ==========================================
class MacAssetManager(QtWidgets.QWidget):
    def __init__(self):
        super(MacAssetManager, self).__init__()
        self.setWindowTitle("Mac Asset Manager - 视效素材管理器")
        self.resize(1200, 800)
        self.setStyleSheet(MAC_STYLE_QSS)

        # 初始化库文件夹
        if not os.path.exists(MAC_ASSET_ROOT):
            try:
                os.makedirs(MAC_ASSET_ROOT)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "初始化失败", f"无法创建主库目录: {e}")

        self.current_group_path = ""
        self.init_ui()
        self.load_groups()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # ================= 左侧：组(Group)管理 =================
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        header_label = QtWidgets.QLabel("📂 素材组管理 (Groups)")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        left_layout.addWidget(header_label)

        self.group_list = QtWidgets.QListWidget()
        self.group_list.itemClicked.connect(self.on_group_selected)
        left_layout.addWidget(self.group_list)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add_group = QtWidgets.QPushButton("+ 新建组")
        self.btn_add_group.clicked.connect(self.create_new_group)
        self.btn_del_group = QtWidgets.QPushButton("- 删除组")
        self.btn_del_group.clicked.connect(self.delete_current_group)
        
        btn_layout.addWidget(self.btn_add_group)
        btn_layout.addWidget(self.btn_del_group)
        left_layout.addLayout(btn_layout)

        btn_open_root = QtWidgets.QPushButton("在 Finder 中打开主库")
        btn_open_root.clicked.connect(lambda: open_with_mac_default(MAC_ASSET_ROOT))
        left_layout.addWidget(btn_open_root)

        # ================= 右侧：素材展示区 =================
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QtWidgets.QLabel("请在左侧选择或创建一个组，然后将图片拖入下方区域。")
        self.status_label.setStyleSheet("color: #888888;")
        right_layout.addWidget(self.status_label)

        self.asset_view = AssetViewport()
        self.asset_view.files_dropped.connect(self.handle_files_dropped)
        self.asset_view.itemDoubleClicked.connect(self.on_asset_double_clicked)
        right_layout.addWidget(self.asset_view)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([250, 950])

        main_layout.addWidget(splitter)

    # --- 组(文件夹)管理逻辑 ---
    def load_groups(self):
        """扫描主目录，将所有子文件夹作为组加载到左侧"""
        self.group_list.clear()
        if not os.path.exists(MAC_ASSET_ROOT): return
        
        for item in sorted(os.listdir(MAC_ASSET_ROOT)):
            full_path = os.path.join(MAC_ASSET_ROOT, item).replace("\\", "/")
            if os.path.isdir(full_path):
                list_item = QtWidgets.QListWidgetItem(item)
                list_item.setData(QtCore.Qt.UserRole, full_path)
                # 使用系统自带的文件夹图标
                list_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
                self.group_list.addItem(list_item)
                
        if self.group_list.count() > 0:
            self.group_list.setCurrentRow(0)
            self.on_group_selected(self.group_list.item(0))
        else:
            self.current_group_path = ""
            self.asset_view.clear()

    def create_new_group(self):
        group_name, ok = QtWidgets.QInputDialog.getText(
            self, "新建组", "请输入新素材组的名称:", QtWidgets.QLineEdit.Normal, "New_Group"
        )
        if ok and group_name:
            group_path = os.path.join(MAC_ASSET_ROOT, group_name).replace("\\", "/")
            if not os.path.exists(group_path):
                os.makedirs(group_path)
                self.load_groups()
                
                # 自动选中刚创建的组
                items = self.group_list.findItems(group_name, QtCore.Qt.MatchExactly)
                if items:
                    self.group_list.setCurrentItem(items[0])
                    self.on_group_selected(items[0])
            else:
                QtWidgets.QMessageBox.warning(self, "警告", "同名组已存在！")

    def delete_current_group(self):
        item = self.group_list.currentItem()
        if not item: return
        
        group_name = item.text()
        group_path = item.data(QtCore.Qt.UserRole)
        
        reply = QtWidgets.QMessageBox.question(
            self, '确认删除', 
            f"确定要删除组 '{group_name}' 及其包含的所有素材文件吗？\n此操作不可撤销！", 
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                shutil.rmtree(group_path)
                self.load_groups()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "删除失败", str(e))

    def on_group_selected(self, item):
        self.current_group_path = item.data(QtCore.Qt.UserRole)
        self.status_label.setText(f"当前组: {item.text()} (路径: {self.current_group_path})")
        self.refresh_assets()

    # --- 素材扫描与展示逻辑 ---
    def refresh_assets(self):
        self.asset_view.clear()
        if not self.current_group_path or not os.path.exists(self.current_group_path):
            return

        for f in os.listdir(self.current_group_path):
            ext = os.path.splitext(f)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                full_path = os.path.join(self.current_group_path, f).replace("\\", "/")
                self.add_asset_item(full_path)

    def add_asset_item(self, path):
        name = os.path.basename(path)
        item = QtWidgets.QListWidgetItem(name)
        item.setData(QtCore.Qt.UserRole, path)
        
        # 提取缩略图，针对常见图片格式
        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            # 生成高清缩略图并裁剪成正方形以保持 UI 整洁
            scaled = pixmap.scaled(300, 300, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
            item.setIcon(QtGui.QIcon(scaled))
        else:
            # 如果是 EXR 或无法读取的图，给个默认图标
            item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
            
        self.asset_view.addItem(item)

    # --- 拖拽导入逻辑 ---
    def handle_files_dropped(self, file_paths):
        if not self.current_group_path:
            QtWidgets.QMessageBox.warning(self, "提示", "请先在左侧选择或创建一个组！")
            return
            
        success_count = 0
        for path in file_paths:
            if not os.path.isfile(path): continue
            ext = os.path.splitext(path)[1].lower()
            if ext not in ALLOWED_EXTENSIONS: continue
            
            filename = os.path.basename(path)
            target_path = os.path.join(self.current_group_path, filename).replace("\\", "/")
            
            # 避免覆盖重名文件
            if os.path.exists(target_path):
                base, ext_name = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(self.current_group_path, f"{base}_{counter}{ext_name}").replace("\\", "/")):
                    counter += 1
                target_path = os.path.join(self.current_group_path, f"{base}_{counter}{ext_name}").replace("\\", "/")
                
            try:
                shutil.copy2(path, target_path)
                success_count += 1
            except Exception as e:
                print(f"导入 {filename} 失败: {e}")
                
        if success_count > 0:
            self.refresh_assets()

    # --- 双击操作逻辑 (核心需求：编辑/新建对应的 TXT) ---
    def on_asset_double_clicked(self, item):
        image_path = item.data(QtCore.Qt.UserRole)
        dir_name = os.path.dirname(image_path)
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # 推导同名 txt 路径
        txt_path = os.path.join(dir_name, base_name + ".txt").replace("\\", "/")
        
        # 同目录下没有txt文档那就新建一个同名文档
        if not os.path.exists(txt_path):
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"// Prompt for {base_name}\n\n")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"无法创建文本文档:\n{e}")
                return
                
        # 调用 macOS 原生命令打开文档
        open_with_mac_default(txt_path)


if __name__ == "__main__":
    # 适配高分屏支持
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    app = QtWidgets.QApplication(sys.argv)
    
    manager = MacAssetManager()
    manager.show()
    
    sys.exit(app.exec_() if hasattr(app, "exec_") else app.exec())