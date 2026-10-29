---
name: fix-bug
description: Doc danh sach loi trong bug/Error.txt (hoac loi nguoi dung mo ta), tim nguyen nhan, sua, kiem tra va ghi lich su fix. Dung khi nguoi dung go /fix-bug hoac nho "fix loi trong file bug".
---
# Quy trinh fix bug

1. Lay danh sach loi: tu tham so nguoi dung dua, neu khong co thi doc `bug/Error.txt`.
2. Voi moi loi:
   - Tim code lien quan bang Grep (hoac subagent `finder`), chi doc doan can thiet.
   - Xac dinh nguyen nhan goc truoc khi sua. Neu loi mo ho -> hoi lai nguoi dung.
   - Sua toi thieu, tuan thu "Luu y quan trong khi code" trong CLAUDE.md.
3. Kiem tra: `python -c "from app import create_app; create_app()"` khong loi; neu co test thi chay test.
4. Ghi 1-2 dong (nguyen nhan + fix) vao dau `bug/lich_su_fix.md`, duoi tieu de ngay hom nay.
5. Neu loi la mot "bay" de lap lai -> them quy tac vao muc "Luu y quan trong khi code" trong CLAUDE.md.
6. Tom tat cho nguoi dung bang tieng Viet: loi nao da fix, loi nao chua va vi sao.
7. Commit theo "Git workflow" trong CLAUDE.md khi nguoi dung dong y.
