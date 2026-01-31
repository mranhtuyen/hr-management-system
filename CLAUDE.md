# HR Management System - Project Context

## Tong quan
He thong quan ly nhan su cho chuoi quan ca phe, xay dung bang Python Flask.

## Cong nghe
- Backend: Flask 3.0, SQLAlchemy, Flask-Login
- Frontend: Jinja2 + Tailwind CSS
- Database: SQLite (dev) / PostgreSQL (prod)
- Auth: Role-based (Admin/Manager/Staff)

## Cau truc thu muc chinh
```
app/
  auth/         - Dang nhap, phan quyen
  dashboard/    - Trang chu theo role
  employee/     - Quan ly nhan vien
  schedule/     - Dang ky va xep lich lam viec
  attendance/   - Cham cong, import Excel
  payroll/      - Tinh luong, phieu luong
  violation/    - Quan ly vi pham
  reward/       - Quan ly khen thuong
  models.py     - Database models
  templates/    - Jinja2 templates
```

## Cac tinh nang da hoan thanh
1. Quan ly nhan vien (CRUD)
2. Dang ky lich lam viec (NV dang ky, Admin duyet)
3. Xep lich tu dong (cau hinh 2/3/4 NV moi ca)
4. Import cham cong tu Excel (row + pivot format)
5. Tinh luong tu dong
6. Xu ly di muon, tinh phat
7. Quan ly vi pham, khen thuong

## Commits gan day
- 57bfa84: Fix CSRF issues and add schedule management features
- a18ae04: Initial commit

## Luu y khi lam viec
- CSRF token can thiet cho moi form POST
- SQLAlchemy join can dung .select_from() khi co nhieu bang
- Template dung string keys cho shift_type ('morning', 'afternoon', 'evening')
- Kiem tra None truoc khi goi .strftime()

## Cach chay
```bash
cd D:\Claude_Code\hr-management-system
python run.py
# Server: http://127.0.0.1:5000
# Admin: admin / admin123
```

## Thu muc bug reports
`bug/` - Chua file bao loi (.docx, .txt) va file mau (.xlsx)
