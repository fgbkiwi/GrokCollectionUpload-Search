import flet as ft

print("Checking ft.Icons.REFRESH...")

try:
    # Use the correct enum/constant for the icon
    icon = ft.Icon(ft.Icons.REFRESH)
    print(f"Icon created successfully: {icon}")
except Exception as e:
    print(f"Error creating Icon: {e}")
