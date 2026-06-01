import os

gui_dir = 'C:/Users/chaos/AppData/Local/Programs/UsageTracker'
cli_dir = 'D:/app/UsageTracker'

for d, label in [(gui_dir, 'GUI版本(C盘)'), (cli_dir, 'CLI版本(D盘)')]:
    if os.path.exists(d):
        print(f'EXISTS: {label} -> {d}')
        try:
            files = os.listdir(d)[:10]
            for f in files:
                print(f'  {f}')
        except Exception as e:
            print(f'  Error listing: {e}')
    else:
        print(f'NOT FOUND: {label} -> {d}')
