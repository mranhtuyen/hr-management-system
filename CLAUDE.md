# HR Management System - Project Context

## Tong quan
He thong quan ly nhan su cho chuoi quan ca phe, xay dung bang Python Flask.

## Cong nghe
- Backend: Flask 3.0, SQLAlchemy, Flask-Login, Flask-WTF (CSRF)
- Frontend: Jinja2 + Tailwind CSS + Alpine.js
- Database: SQLite (dev) / PostgreSQL (prod)
- Auth: Role-based (Admin/Manager/Staff)

## Cach chay
```bash
cd D:\Claude_Code\hr-management-system
python run.py
# Server: http://127.0.0.1:5000
# Admin: admin / admin123
```

## Cau truc thu muc chinh
```
app/
  __init__.py       - App factory, CSRF setup
  models.py         - Database models (User, WorkSchedule, ScheduleShift, etc.)
  auth/             - Dang nhap, phan quyen, quan ly user
  dashboard/        - Trang chu theo role
  schedule/         - Dang ky va xep lich lam viec
    routes.py       - 50+ routes cho schedule management
    auto_scheduler.py - Thuat toan xep lich tu dong
    forms.py        - WeeklyScheduleForm
  attendance/       - Cham cong, import Excel
    routes.py       - Import, view, edit attendance
    import_handler.py - Parse Excel (row + pivot format)
    late_checker.py - Xu ly di muon
  payroll/          - Tinh luong, phieu luong
    routes.py       - CRUD payroll
    calculator.py   - Tinh luong tu dong
    report_generator.py - Xuat PDF
  violation/        - Quan ly vi pham
  reward/           - Quan ly khen thuong
  export/           - Xuat Excel (schedule, attendance, payroll)
  logs/             - Activity logs
  templates/        - Jinja2 templates
```

## Database Models (app/models.py)

### User
- id, username, password_hash, full_name, phone, email
- role: STAFF / MANAGER / ADMIN
- employment_type: PART_TIME / FULL_TIME
- hourly_rate, salary_percentage, meal_support_eligible
- is_probation, probation_salary_rate

### WorkSchedule
- id, user_id, week_start_date, week_end_date
- status: DRAFT / SUBMITTED / APPROVED / LOCKED
- submitted_at, approved_at, approved_by
- Relationship: shifts (ScheduleShift)

### ScheduleShift
- id, schedule_id, date, shift_type (MORNING/AFTERNOON/EVENING)
- shift_start_time, shift_end_time
- is_preferred, is_confirmed, is_and_condition
- shift_source: 'employee' (NV dang ky) / 'system' (he thong xep)
- draft_status: 'draft' (nhap) / 'final' (chinh thuc)

### AttendanceRecord
- id, user_id, date, shift_type
- scheduled_start, scheduled_end, actual_checkin, actual_checkout
- late_minutes, early_departure_minutes, total_work_hours
- is_late, is_early_bird

### Payroll
- id, user_id, month, year
- total_work_hours, total_shifts, late_count
- total_penalty, total_reward, meal_support_amount, advance_payment
- gross_salary, net_salary
- status: DRAFT / APPROVED / PAID

### ScheduleSettings
- deadline_day (0-6), deadline_hour, deadline_minute
- late_registration_message
- allow_current_week_edit

### SystemConfig
- key, value (luu cau hinh mau sac, gio ca)
- shift_morning_color, shift_afternoon_color, shift_evening_color
- shift_morning_start/end, shift_afternoon_start/end, shift_evening_start/end

## Cac tinh nang chinh

### 1. Quan ly nhan vien (Admin)
- CRUD nhan vien
- Phan quyen (Staff/Manager/Admin)
- Cau hinh luong gio, ho tro an ca

### 2. Dang ky lich lam viec (Staff)
- NV dang ky nguyen vong ca lam viec
- Ho tro dang ky nhieu tuan (hien tai, sau, sau nua)
- Deadline cau hinh duoc (mac dinh: 18h Thu 7)
- Sau khi tuan hien tai duoc duyet -> cho phep dang ky tuan ke tiep

### 3. Xep lich tu dong (Admin/Manager)
WORKFLOW 5 BUOC:
1. Chon nhan vien tham gia (`/schedule/select-staff`)
   - Ho tro chon tuan (truoc/hien tai/sau)
2. Cau hinh xep lich (`/schedule/config-auto-schedule`)
   - So NV moi ca (2/3/4)
3. Xem va sua lich NHAP (`/schedule/review-draft`)
   - Ma tran lich theo ngay/ca
   - Them/Xoa NV vao ca (AJAX)
4. Luu lich chinh thuc (`/schedule/save-draft`)
   - Xoa final cu truoc khi luu moi (tranh duplicate)
5. Day lich ve cho NV (`/schedule/publish-to-staff`)

### 4. Xem lich (Staff)
Menu "Lich cua toi" co 2 sub-menu:
- **Lich dang ky** (`/schedule/my-schedule`): Lich NV tu dang ky
- **Lich duoc duyet** (`/schedule/my-approved-schedule`): Lich da confirmed

### 5. Quan ly lich (Admin/Manager)
- Xem lich lam viec (`/schedule/view`)
- Duyet lich dang ky (`/schedule/review`)
- Them/Sua/Xoa ca truc tiep
- Reset lich tuan

### 6. Cham cong
- Import tu Excel (row + pivot format)
- Preview truoc khi luu
- Xem/Sua/Xoa ban ghi cham cong
- Xu ly di muon tu dong

### 7. Tinh luong
- Tinh luong tu dong theo thang
- Chi tiet: gio lam, phat, thuong, an ca, tam ung
- Duyet va danh dau da tra
- Xuat phieu luong PDF

### 8. Cai dat he thong
- Deadline dang ky lich
- Mau sac va gio ca lam viec
- Cho phep/khong cho sua lich tuan hien tai

## Luu y quan trong khi code

### CSRF Token
- Moi form POST can `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
- AJAX JSON request can header: `'X-CSRFToken': '{{ csrf_token() }}'`

### AJAX voi JSON
```python
# DUNG:
if request.is_json:
    data = request.get_json()
    user_id = int(data.get('user_id', 0))
else:
    user_id = request.form.get('user_id', type=int)

# SAI (dict.get() khong co type parameter):
data = request.get_json()
user_id = data.get('user_id', type=int)  # ERROR!
```

### SQLAlchemy
- Join nhieu bang: dung `.select_from()`
- Filter voi datetime: Ternary can dau ngoac
```python
# SAI:
Reward.created_at < datetime(...) if month < 12 else datetime(...)
# DUNG:
Reward.created_at < (datetime(...) if month < 12 else datetime(...))
```

### Template
- shift_type dung string keys: 'morning', 'afternoon', 'evening'
- Kiem tra None truoc khi goi .strftime()
- Mau sac ca: bg-yellow-50 (Sang), bg-orange-50 (Chieu), bg-indigo-50 (Toi)

### Tranh duplicate data
- Khi luu lich moi: XOA shifts final cu truoc
- Export Excel: Chi lay is_confirmed=True, loai bo duplicate theo shift_type

## Cac bug da fix gan day

### Session 2026-02-02

1. **SQLAlchemy ArgumentError** trong payroll detail
   - Nguyen nhan: Ternary expression thieu dau ngoac
   - Fix: Tach datetime calculation ra bien rieng

2. **Cai dat mau sac/gio ca khong ap dung**
   - Nguyen nhan: Code dung SHIFT_TIMES hardcoded
   - Fix: Tao get_shift_settings(), get_dynamic_shift_times()

3. **Xep lich tu dong luon nhay sang tuan sau**
   - Fix: Them week_offset parameter cho select_staff()

4. **Xem cham cong thieu chuc nang Sua/Xoa**
   - Fix: Them routes update_record(), delete_record()

5. **Excel xuat du lieu trung lap**
   - Nguyen nhan: Moi lan luu them moi, khong xoa cu
   - Fix: save_draft() xoa final shifts cu truoc khi luu

6. **Them NV vao ca bao "Loi ket noi!"**
   - Nguyen nhan: Parse JSON data sai (dict.get() khong co type)
   - Fix: Dung request.is_json va int(data.get())

7. **Them ca lam viec bao "da ton tai"**
   - Nguyen nhan: Check qua strict, bao gom ca draft
   - Fix: Chi check confirmed shifts

8. **Deadline dang ky khong hoat dong**
   - Nguyen nhan: Logic chi cho dang ky vao Thu 6 + ngay deadline
   - Fix: Cho phep dang ky bat ky ngay nao truoc deadline

9. **NV khong dang ky duoc tuan ke tiep**
   - Nguyen nhan: Block khi tuan hien tai approved
   - Fix: Tu dong chuyen sang dang ky tuan tiep theo

## Thu muc bug reports
`bug/` - Chua file bao loi (.docx, .txt) va file mau (.xlsx)
- Error.txt: Danh sach loi can fix
- excel.txt: Mau du lieu export bi trung lap
- bao_cao_fix_lanX.txt: Lich su fix bug

## Git workflow
```bash
# Xem thay doi
git status
git diff

# Commit
git add <files>
git commit -m "Fix: mo ta ngan gon

Chi tiet thay doi...

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Push
git push origin main
```
