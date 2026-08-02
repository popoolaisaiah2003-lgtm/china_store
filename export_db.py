import os
import pymysql
from datetime import datetime, date

conn = pymysql.connect(host='127.0.0.1', user='root', password='', db='yan_zhen_peptide', charset='utf8mb4')
cursor = conn.cursor()

tables = ['admins', 'categories', 'products', 'product_images', 'coas', 'blog_posts', 'comments', 'reviews', 'order_records', 'shipment_updates', 'settings', 'alembic_version']

sql_lines = ['SET FOREIGN_KEY_CHECKS=0;']

for t in tables:
    try:
        cursor.execute(f'SHOW CREATE TABLE `{t}`')
        create_stmt = cursor.fetchone()[1]
        sql_lines.append(f'DROP TABLE IF EXISTS `{t}`;')
        sql_lines.append(create_stmt + ';')
        
        cursor.execute(f'SELECT * FROM `{t}`')
        rows = cursor.fetchall()
        if rows:
            cursor.execute(f'SHOW COLUMNS FROM `{t}`')
            cols = ', '.join([f'`{col[0]}`' for col in cursor.fetchall()])
            for row in rows:
                vals = []
                for v in row:
                    if v is None:
                        vals.append('NULL')
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    elif isinstance(v, bool):
                        vals.append('1' if v else '0')
                    elif isinstance(v, (datetime, date)):
                        vals.append(f"'{v.strftime('%Y-%m-%d %H:%M:%S')}'")
                    elif isinstance(v, bytes):
                        vals.append('0x' + v.hex())
                    else:
                        esc = str(v).replace('\\', '\\\\').replace("'", "''")
                        vals.append(f"'{esc}'")
                val_str = ', '.join(vals)
                sql_lines.append(f"INSERT INTO `{t}` ({cols}) VALUES ({val_str});")
    except Exception as e:
        print(f"Error on table {t}: {e}")

sql_lines.append('SET FOREIGN_KEY_CHECKS=1;')

with open('yan_zhen_peptide.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_lines))

print("Created yan_zhen_peptide.sql successfully!")
