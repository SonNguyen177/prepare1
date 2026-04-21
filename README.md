## README.md
- Setup từ 1 folder git, chỉ có file gitignore
- Copy source code, ko có các file markdown
- Chạy /claude trên thư mục
- Chọn đúng model = /model opus 4.6
- init file CLAUDE.md = /init
- Thực hiện đọc codebase/ build context từ bmad

// check nodejs version
node -v
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
nvm install 25

// chuyen thu mục lam viec:

cd /Users/bobby/DATA/AI\ /Claude\ Code/Hackathon/bmad-engine

//install bmad

npx bmad-method install

- Sau khi cài đặt xong mở thư mục repo bằng VSCode
- Kiểm tra các folder _bmad đã sinh ra

// chạy claude trên thư mục hiện tại
 claude

 Bước 1: Đọc codebase và tạo context cho dự án : 
 /bmad-generate-project-context : +2 phút
 - ghi xuống thành các section của project-context.md (7 categories : tech stack, language-rule, framework-rules, testing-rules, code quality, workflow rule, critical-rules) => hoàn thành sau hơn +10 phút