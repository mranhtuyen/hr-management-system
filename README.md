# HR Management System

He thong quan tri nhan su tu dong cho chuoi cua hang ca phe.

## Tinh nang chinh

- **Dang ky lich lam viec**: Nhan vien dang ky lich hang tuan, he thong tu dong xep lich
- **Cham cong**: Import du lieu tu may cham cong, phat hien di muon tu dong
- **Tinh luong**: Tu dong tinh luong, phat, thuong, ho tro an ca
- **Thong bao**: Email, SMS nhac nho va canh bao
- **Bao cao**: Xuat bao cao PDF, thong ke

## Cong nghe

- **Backend**: Python Flask 3.0
- **Database**: PostgreSQL 15
- **Frontend**: Tailwind CSS, Alpine.js
- **Background Jobs**: APScheduler
- **PDF**: ReportLab

## Cai dat

### Yeu cau

- Python 3.11+
- PostgreSQL 15+
- Docker (khyen nghi)

### Cach 1: Docker (Khyen nghi)

```bash
# Clone project
cd hr-management-system

# Chay voi Docker Compose
docker-compose up -d

# Tao database tables
docker-compose exec web flask db upgrade

# Tao du lieu mau
docker-compose exec web flask seed

# Truy cap: http://localhost:5000
```

### Cach 2: Cai dat thu cong

```bash
# Tao virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Cai dat dependencies
pip install -r requirements.txt

# Cau hinh database
cp .env.example .env
# Sua file .env voi thong tin database cua ban

# Tao database tables
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Tao du lieu mau
flask seed

# Chay ung dung
python run.py
```

## Tai khoan mac dinh

Sau khi chay `flask seed`:

| Vai tro | Username | Password |
|---------|----------|----------|
| Admin | admin | admin123 |
| Manager | manager | manager123 |
| Staff | staff1 - staff5 | staff123 |

## Cau truc thu muc

```
hr-management-system/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py             # Database models
│   ├── auth/                 # Authentication module
│   ├── dashboard/            # Dashboard module
│   ├── schedule/             # Lich lam viec module
│   ├── attendance/           # Cham cong module
│   ├── payroll/              # Tinh luong module
│   ├── notifications/        # Thong bao module
│   ├── scheduler/            # Background jobs
│   ├── static/               # CSS, JS, images
│   └── templates/            # Jinja2 templates
├── migrations/               # Database migrations
├── uploads/                  # File upload
├── exports/                  # Exported reports
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── docker-compose.yml        # Docker setup
└── run.py                    # Entry point
```

## Huong dan su dung

### Nhan vien (Staff)

1. **Dang ky lich**: Vao "Dang ky lich" > Chon cac ca muon lam > Gui dang ky
2. **Xem lich**: Vao "Lich cua toi" de xem lich da duoc duyet
3. **Xem cham cong**: Vao "Cham cong" de xem gio lam va di muon
4. **Xem luong**: Vao "Luong" de xem phieu luong

### Quan ly (Manager/Admin)

1. **Duyet lich**: Vao "Duyet lich" > Xem va duyet lich cua nhan vien
2. **Xep lich tu dong**: Nhan "Xep lich tu dong" de he thong tu xep
3. **Import cham cong**: Vao "Import cham cong" > Upload file Excel
4. **Tinh luong**: Vao "Bang luong" > Nhan "Tinh luong"
5. **Quan ly NV**: Vao "Nhan vien" de them/sua nhan vien

## Quy tac nghiep vu

### Xep lich tu dong

1. Moi ca co 2 nhan vien chinh
2. Gio dong co the them NV thu 3 (dua vao du lieu iPOS)
3. Moi NV nghi it nhat 1 ngay/tuan
4. Uu tien nguyen vong NV (theo thoi gian gui)
5. Can bang so ca giua cac NV

### Tinh phat di muon

| Lan | Tien phat |
|-----|-----------|
| 1 | 0d (Nhac nho) |
| 2 | 50,000d |
| 3+ | 100,000d/lan |

### Tinh luong

```
Thuc linh = (Gio lam x Luong gio x Ty le) + An ca + Thuong - Phat - Tam ung
```

- Ty le: 90% (thu viec), 100% (chinh thuc)
- An ca: 25,000d/ngay (Full-time >= 8h)
- Ngay le: Nhan he so 200% hoac 300%

## Background Jobs

| Job | Lich | Mo ta |
|-----|------|-------|
| Mo dang ky | Thu 6, 8h | Gui email mo dang ky |
| Nhac nho | Thu 7, 12h | Nhac NV chua dang ky |
| Khoa dang ky | Thu 7, 18h | Khoa form dang ky |
| Xep lich | CN, 8h | Chay thuat toan xep lich |
| Xu ly cham cong | Hang ngay, 19h | Phat hien di muon |
| Tinh luong | Ngay 1, 8h | Tinh luong thang truoc |

## API Endpoints

| Endpoint | Method | Mo ta |
|----------|--------|-------|
| /auth/login | GET, POST | Dang nhap |
| /dashboard/ | GET | Dashboard |
| /schedule/register | GET, POST | Dang ky lich |
| /schedule/view | GET | Xem lich |
| /attendance/import | GET, POST | Import cham cong |
| /payroll/list | GET | Danh sach luong |

## Lien he

- **Architect**: Claude (Vibecode Kit v4.0)
- **Client**: Mr. Tuyen
- **Date**: 31/01/2026

## License

Private - All rights reserved.
