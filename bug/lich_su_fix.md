# Lich su fix bug

Ghi moi nhat len tren. Moi muc: nguyen nhan + cach fix (1-2 dong).

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
