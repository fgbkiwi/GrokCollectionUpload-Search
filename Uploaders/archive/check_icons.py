#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication, QStyle, QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QIcon

def check_icons():
    app = QApplication(sys.argv)
    print("Checking PyQt6 Standard Icons...")
    
    # List of some standard icons to check
    icons_to_check = [
        ("SP_BrowserReload", QStyle.StandardPixmap.SP_BrowserReload),
        ("SP_FileIcon", QStyle.StandardPixmap.SP_FileIcon),
        ("SP_DirIcon", QStyle.StandardPixmap.SP_DirIcon),
        ("SP_DialogOkButton", QStyle.StandardPixmap.SP_DialogOkButton),
        ("SP_DialogCancelButton", QStyle.StandardPixmap.SP_DialogCancelButton),
        ("SP_MessageBoxInformation", QStyle.StandardPixmap.SP_MessageBoxInformation),
        ("SP_MessageBoxCritical", QStyle.StandardPixmap.SP_MessageBoxCritical),
    ]
    
    window = QWidget()
    window.setWindowTitle("PyQt6 Icon Check")
    layout = QVBoxLayout(window)
    
    for name, pixmap in icons_to_check:
        try:
            icon = app.style().standardIcon(pixmap)
            if not icon.isNull():
                print(f"✅ Icon {name} created successfully.")
                label = QLabel(f"Icon: {name}")
                # We can't easily display the icon in terminal, so we just log it
            else:
                print(f"❌ Icon {name} is null.")
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            
    print("\nIcon check complete.")
    # We don't actually need to show the window for a check script, 
    # but we could if we wanted to verify visually.
    # window.show()
    # sys.exit(app.exec())

if __name__ == "__main__":
    check_icons()
