import threading
import re
import random
import webview
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__, static_folder='statics')
app.secret_key = "cyberaware_secret_key_protection_2026"  # Khóa bảo mật Flask Session

# CẤU HÌNH AN TOÀN: Khóa môi trường Sandbox (Chỉ diễn tập nội bộ, cấm gửi email thực)
SANDBOX_SAFETY_LOCK = True

# Danh sách tên ngẫu nhiên để khởi tạo bảng xếp hạng và người dùng mẫu
RANDOM_NAMES = [
    "Nguyễn Văn An", "Trần Thị Bích", "Lê Hoàng Cường", "Phạm Minh Đức", 
    "Vũ Thị Hoa", "Đặng Quốc Khánh", "Bùi Phương Linh", "Đỗ Nam Phong"
]

# Cơ sở dữ liệu người dùng & hệ thống lưu tạm trong bộ nhớ
db_users = [
    {
        "id": 1, 
        "username": "admin", 
        "password": "123", 
        "name": "Quản Trị Viên", 
        "role": "admin", 
        "score": 100, 
        "reports": 5, 
        "traps": 0, 
        "risk_level": "Thấp",
        "pre_score": 100,
        "post_score": 100
    },
    {
        "id": 2, 
        "username": "nguyenvanan", 
        "password": "123", 
        "name": "Nguyễn Văn An", 
        "role": "user", 
        "score": 85, 
        "reports": 3, 
        "traps": 0, 
        "risk_level": "Thấp",
        "pre_score": 75,
        "post_score": 85
    },
    {
        "id": 3, 
        "username": "tranthibich", 
        "password": "123", 
        "name": "Trần Thị Bích", 
        "role": "user", 
        "score": 40, 
        "reports": 1, 
        "traps": 3, 
        "risk_level": "Cao",
        "pre_score": 30,
        "post_score": 40
    },
    {
        "id": 4, 
        "username": "lehoangcuong", 
        "password": "123", 
        "name": "Lê Hoàng Cường", 
        "role": "user", 
        "score": 95, 
        "reports": 5, 
        "traps": 0, 
        "risk_level": "Thấp",
        "pre_score": 90,
        "post_score": 95
    },
    {
        "id": 5, 
        "username": "phamminhduc", 
        "password": "123", 
        "name": "Phạm Minh Đức", 
        "role": "user", 
        "score": 30, 
        "reports": 0, 
        "traps": 4, 
        "risk_level": "Rất Cao",
        "pre_score": 20,
        "post_score": 30
    },
    {
        "id": 6, 
        "username": "vuthihoa", 
        "password": "123", 
        "name": "Vũ Thị Hoa", 
        "role": "user", 
        "score": 55, 
        "reports": 2, 
        "traps": 2, 
        "risk_level": "Trung bình",
        "pre_score": 50,
        "post_score": 55
    }
]

db_session = {
    "pre_test": {},
    "post_test": {},
    "simulation_history": [],
    "game_score": 0,
    "badges": [],
    "total_points": 0
}

# DECORATOR KIỂM TRA ĐĂNG NHẬP VÀ PHÂN QUYỀN
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "401 Unauthorized"}), 401
        if session.get('role') != 'admin':
            return jsonify({"status": "error", "message": "403 Forbidden: Bạn không có quyền truy cập tính năng Quản trị viên!"}), 403
        return f(*args, **kwargs)
    return decorated_function

# KỊCH BẢN CHI TIẾT NÂNG CẠO THEO VAI TRÒ
ROLE_SCENARIOS = {
    "accountant": [
        {
            "id": "acc_1",
            "type": "Spear Phishing",
            "title": "Email [GẤP - MẬT] Chỉ đạo Thanh toán Hợp đồng Tư vấn M&A Dự án Q3",
            "desc": "Email mạo danh CEO yêu cầu Kế toán trưởng ủy nhiệm chi gấp 245 triệu cho Đơn vị Tư vấn Pháp lý trước 16h30.",
            "trap_reason": "Bạn đã sập bẫy Giả mạo Lãnh đạo (CEO Scam)! Email sử dụng tên miền mạo danh @company-executive-portal.com (tên miền thật là @company.com). Quy trình an toàn: Tuyệt đối không chuyển tiền chỉ dựa vào Email/Tin nhắn mà không xác minh qua Kênh thứ 2 (Out-of-band) như gọi điện trực tiếp cho CEO hoặc Kế toán trưởng.",
            "content": "Chào chị Kế toán trưởng và Ban Tài chính,\n\nTôi đang trong phiên họp kín với Hội đồng Quản trị và các đối tác Quỹ đầu tư nước ngoài để chốt hợp đồng M&A dự án mới. Vì lý do bảo mật thông tin niêm yết, hợp đồng này chưa thể công bố rộng rãi trong toàn công ty.\n\nĐể đảm bảo thỏa thuận không bị hủy bỏ, vui lòng thực hiện lệnh ủy nhiệm chi khẩn cấp số tiền 245.000.000 VNĐ (Hai trăm bốn mươi lăm triệu đồng) cho Đơn vị Tư vấn Pháp lý độc lập theo thông tin hóa đơn đính kèm. Hạn chót hoàn tất giao dịch là trước 16:30 chiều nay.\n\nVui lòng truy cập đường dẫn sau để xem Hóa đơn & Dự thảo ủy nhiệm chi: http://company-executive-portal.com/invoice-ma-q3\n\nLưu ý: Do tính chất bảo mật của thương vụ, tuyệt đối không thảo luận qua Chat nhóm chung hay hỏi lại các phòng ban khác."
        },
        {
            "id": "acc_video_2",
                        "type": "Deepfake Video Call",
                        "title": "Cuộc gọi khẩn cấp từ Giám đốc Tài chính: Duyệt lệnh chuyển tiền gấp qua video",
                        "desc": "Nhân viên kế toán nhận được cuộc gọi video từ tài khoản của Giám đốc tài chính (CFO)...",
                        "video_url": "/statics/videos/test.mp4",  # Đường dẫn tới file video có sẵn của bạn
                        "duration": "00:10",
                        "video_script": "Chào em, anh đang kẹt ở phòng chờ sân bay...",
                        "subtle_clues": [
                            "Tần suất chớp mắt ít hơn bình thường.",
                            "Viền cổ và tai có vùng mờ nhòe.",
                            "Âm thanh lệch pha so với khẩu hình môi."
                        ],
                        "correct_action": "Cúp máy ngay lập tức và xác thực lại qua số điện thoại nội bộ chính thống."
        },
        {
            "id": "acc_2_2",
            "type": "Deepfake Call",
            "title": "Video Call Deepfake #2: Chủ tịch HĐQT Giả mạo Báo Lỗi Kiểm toán Thuế Khẩn",
            "desc": "Chủ tịch HĐQT xuất hiện qua Video Call thông báo đang thanh tra Thuế và cần nộp phạt gấp 150 triệu.",
            "trap_reason": "Bạn đã sập bẫy Deepfake mạo danh Chủ tịch! Kẻ gian dùng AI tổng hợp khuôn mặt Chủ tịch từ các video sự kiện công ty. Quy trình an toàn: Xác minh lại quy trình tài chính và kiểm tra tính pháp lý của quyết định thanh tra.",
            "content": "\"Chào em, anh đang ngồi làm việc trực tiếp với Đoàn Thanh tra Thuế TP. Hệ thống kế toán bên mình bị phát hiện lệch sổ sách 3 năm qua và họ đang dọa phong tỏa tài khoản ngân hàng công ty ngay trong hôm nay.\n\nAnh cần em chuyển ngay 150 triệu vào tài khoản ký quỹ của Thanh tra để tạm hoãn lệnh phong tỏa trong lúc anh giải trình. Làm gấp giúp anh, tình huống này rất nguy cấp!\""
        },
        {
            "id": "acc_3",
            "type": "Multi-stage Scam",
            "title": "Cảnh báo Lỗi Giao dịch Ngân hàng Doanh nghiệp (SMS Brandname)",
            "desc": "Tin nhắn giả mạo Ngân hàng thông báo lệnh chuyển tiền bị dừng, yêu cầu truy cập link Phishing để nhập OTP.",
            "trap_reason": "Bạn đã bị dụ bấm vào trang web Phishing cướp tài khoản Ngân hàng! Ngân hàng không bao giờ gửi đường link yêu cầu nhập Mật khẩu / mã OTP hủy giao dịch qua SMS. Luôn kiểm tra địa chỉ Web chính thức.",
            "content": "[Vietcombank-iB Alert]: Hệ thống phát hiện Lệnh chuyển tiền số ID-883921 (Số tiền: 500,000,000 VND) của Quý khách bị tạm dừng do nghi vấn giao dịch bất thường. Nếu KHÔNG phải bạn thực hiện, vui lòng truy cập ngay https://vcb-digibank-corp-verify.net để hủy lệnh và xác thực lại mã OTP Doanh nghiệp trước 17:00."
        }
    ],
    "hr": [
        {
            "id": "hr_1",
            "type": "Spear Phishing",
            "title": "CV Ứng tuyển Cấp cao Chứa Mã độc Mã hóa Dữ liệu (Ransomware)",
            "desc": "Email từ ứng viên vị trí Giám đốc đính kèm file Ho_So_Nang_Luc.zip có mật khẩu và yêu cầu Bật Macro/Enable Content.",
            "trap_reason": "Bạn đã kích hoạt Mã độc Mã hóa Dữ liệu (Ransomware)! Kẻ tấn công dùng file .zip có mật khẩu để qua mặt các hệ thống Quét Virus tự động của Email. Việc yêu cầu 'Enable Macro/Content' trong file Word thực chất là chạy script độc hại đánh cắp dữ liệu máy tính.",
            "content": "Kính gửi Ban Giám đốc và Bộ phận Nhân sự (HR),\n\nTôi xin gửi Hồ sơ ứng tuyển vị trí Giám đốc Kinh doanh theo thông tin tuyển dụng của Công ty. Tôi có hơn 10 năm kinh nghiệm điều hành tại các Tập đoàn đa quốc gia.\n\nDo thông tin về Bảng lương cũ và Danh sách Dự án đã từng thực hiện có tính chất bảo mật riêng tư, tôi đã nén toàn bộ văn bằng, CV và Bảng lương vào file đính kèm dưới dạng mã hóa:\n📁 File đính kèm: Ho_So_Nang_Luc_Ung_Vien_NguyenVanHung.zip (Mật khẩu giải nén: 123456)\n\nVui lòng giải nén, mở file Word và bấm \"Enable Editing / Enable Content\" để xem đầy đủ nội dung dự án. Rất mong nhận được phản hồi lịch phỏng vấn."
        },
        {
            "id": "hr_2",
            "type": "Deepfake Video Call",
            "title": "Cuộc gọi khẩn cấp từ Giám đốc Tài chính: Duyệt lệnh chuyển tiền gấp qua video",
                "desc": "Nhân viên kế toán nhận được cuộc gọi video từ tài khoản của Giám đốc tài chính (CFO)...",
                "video_url": "/statics/videos/test1.mp4",  # Đường dẫn tới file video có sẵn của bạn
                "duration": "00:10",
                "video_script": "Chào em, anh đang kẹt ở phòng chờ sân bay...",
                "subtle_clues": [
                    "Tần suất chớp mắt ít hơn bình thường.",
                    "Viền cổ và tai có vùng mờ nhòe.",
                    "Âm thanh lệch pha so với khẩu hình môi."
                ],
                "correct_action": "Cúp máy ngay lập tức và xác thực lại qua số điện thoại nội bộ chính thống."
        },
        {
            "id": "hr_3",
            "type": "Multi-stage Scam",
            "title": "Cập nhật Quy chế Lương thưởng & Đánh giá KPI Năm 2026",
            "desc": "Email giả danh Phòng CNTT gửi link đăng nhập Microsoft 365 giả mạo để xem file KPI.",
            "trap_reason": "Bạn đã bị đánh cắp Tài khoản Microsoft 365 / Email Công ty! Cổng đăng nhập mạo danh portal-office365-corp-update.com thu thập Tên đăng nhập & Mật khẩu của bạn.",
            "content": "Kính gửi Toàn thể Cán bộ Nhân viên,\n\nBan Giám đốc vừa phê duyệt Quy chế Tính thưởng KPI và Điều chỉnh Bảng lương mới áp dụng từ Q3/2026. Tất cả nhân sự bắt buộc phải truy cập để xác nhận thông tin thụ hưởng và mức đóng BHXH mới.\n\nVui lòng đăng nhập vào Hệ thống Portal Nhân sự Công ty tại link: http://portal-office365-corp-update.com/kpi-2026\n\n(Lưu ý: Sử dụng Mật khẩu Email công ty để xác thực quyền truy cập)."
        }
    ],
    "it": [
        {
            "id": "it_1",
            "type": "Spear Phishing",
            "title": "Cảnh báo Khẩn: Chứng chỉ SSL/TLS & Cloud Server AWS bị hết hạn",
            "desc": "Email mạo danh AWS Cloud Services yêu cầu đăng nhập tài khoản Root để gia hạn API Key.",
            "trap_reason": "Bạn đã nhập API Key / Credentials hệ thống Cloud lên tên miền giả mạo! Tên miền aws-console-verify.net là tên miền phishing. Kẻ tấn công sẽ chiếm quyền điều khiển toàn bộ hạ tầng Cloud của tổ chức.",
            "content": "CRITICAL NOTICE: SSL Certificate & Wildcard DNS cho hệ thống Core Doanh nghiệp sẽ bị hết hạn và chấm dứt kết nối sau 2 giờ nữa do lỗi đồng bộ billing.\n\nVui lòng truy cập ngay cổng quản trị hạ tầng tại http://aws-console-verify.net, đăng nhập tài khoản Root/Admin và cập nhật Master API Key để hệ thống tự động gia hạn chứng chỉ SSL khẩn cấp."
        },
        {
            "id": "it_2",
            "type": "Deepfake Video Call",
            "title": "Cuộc gọi khẩn cấp từ Giám đốc Tài chính: Duyệt lệnh chuyển tiền gấp qua video",
            "desc": "Nhân viên kế toán nhận được cuộc gọi video từ tài khoản của Giám đốc tài chính (CFO)...",
            "video_url": "/statics/videos/test.mp4",  # Đường dẫn tới file video có sẵn của bạn
            "duration": "00:10",
            "video_script": "Chào em, anh đang kẹt ở phòng chờ sân bay...",
            "subtle_clues": [
                "Tần suất chớp mắt ít hơn bình thường.",
                "Viền cổ và tai có vùng mờ nhòe.",
                "Âm thanh lệch pha so với khẩu hình môi."
            ],
            "correct_action": "Cúp máy ngay lập tức và xác thực lại qua số điện thoại nội bộ chính thống."
        },
        {
            "id": "it_3",
            "type": "Multi-stage Scam",
            "title": "Tấn công Phishing Đánh cắp Token Truy cập Kho Mã nguồn Git / CI-CD",
            "desc": "Cảnh báo mạo danh GitLab/GitHub báo Personal Access Token (PAT) bị lộ, dụ đăng nhập cổng Login giả để reset.",
            "trap_reason": "Bạn đã cung cấp token truy cập và thông tin đăng nhập kho mã nguồn tổ chức trên cổng giả mạo! Kẻ tấn công có thể chèn mã độc vào Source Code (Supply Chain Attack) hoặc đánh cắp toàn bộ sở hữu trí tuệ của công ty.",
            "content": "[GitLab Internal Alert]: Phát hiện Personal Access Token (PAT) và SSH Key của tài khoản Developer của bạn vừa bị rò rỉ trên không gian mạng công cộng. Để đảm bảo an toàn cho Repository dự án, hệ thống đã tạm khóa quyền Push code.\n\nVui lòng truy cập ngay cổng xác thực nội bộ tại http://gitlab-internal-auth.com để đăng nhập và cấp lại Access Token mới trong vòng 12 giờ."
        }
    ],
    "sales": [
        {
            "id": "sales_1",
            "type": "Spear Phishing",
            "title": "Thư Mời Thầu & Yêu cầu Báo Giá Dự án Triển khai Phần mềm 3.2 Tỷ",
            "desc": "Email từ Khách hàng lớn gửi link SharePoint yêu cầu đăng nhập tài khoản Email Doanh nghiệp để tải Hồ sơ Thầu.",
            "trap_reason": "Bạn đã nhập thông tin tài khoản doanh nghiệp vào trang web Phishing giả mạo SharePoint! Kẻ tấn công lợi dụng tâm lý hám lời từ các hợp đồng giá trị cao của nhân viên Sales.",
            "content": "Kính gửi Phòng Kinh doanh,\n\nChúng tôi đại diện cho Tập đoàn SunGroup trân trọng mời Quý công ty tham gia chào giá gói thầu tư vấn triển khai hạ tầng & phần mềm cho dự án sắp tới của chúng tôi (Tổng giá trị dự kiến 3,2 Tỷ VNĐ).\n\nDo yêu cầu bảo mật của Hồ sơ Mời thầu (RFP), toàn bộ File Báo cáo Kỹ thuật và Bảng Tiêu chuẩn đã được tải lên Cổng lưu trữ SharePoint Doanh nghiệp.\n\nVui lòng truy cập đường link http://partner-corp-group.net/rfp-2026 và Đăng nhập bằng Tài khoản Microsoft / Email Doanh nghiệp của bạn để tải Hồ sơ Mời thầu (Hạn nộp báo giá: Trước 12:00 ngày mai)."
        },
        {
            "id": "sales_2",
            "type": "Deepfake Video Call",
            "title": "Cuộc gọi khẩn cấp từ Giám đốc Tài chính: Duyệt lệnh chuyển tiền gấp qua video",
            "desc": "Nhân viên kế toán nhận được cuộc gọi video từ tài khoản của Giám đốc tài chính (CFO)...",
            "video_url": "/statics/videos/test.mp4",  # Đường dẫn tới file video có sẵn của bạn
            "duration": "00:10",
            "video_script": "Chào em, anh đang kẹt ở phòng chờ sân bay...",
            "subtle_clues": [
                "Tần suất chớp mắt ít hơn bình thường.",
                "Viền cổ và tai có vùng mờ nhòe.",
                "Âm thanh lệch pha so với khẩu hình môi."
            ],
            "correct_action": "Cúp máy ngay lập tức và xác thực lại qua số điện thoại nội bộ chính thống."
        },
        {
            "id": "sales_3",
            "type": "Multi-stage Scam",
            "title": "Xác nhận Đơn đặt hàng Xuất khẩu Khẩn (Gửi đính kèm File .exe ẩn dưới dạng PDF)",
            "desc": "Khách hàng nước ngoài gửi file Purchase_Order_2026.pdf.exe yêu cầu mở xem số lượng hàng.",
            "trap_reason": "Bạn đã bị cài Trojan / Spyware theo dõi bàn phím! Kẻ gian thực hiện kịch bản đổi đuôi file double-extension (.pdf.exe) để lừa người dùng bấm vào chạy file thực thi.",
            "content": "Dear Sales Team,\n\nPlease find attached our official Purchase Order (PO) for Q3 shipment. We need 5,000 units delivered by next month.\n\n📁 Attached File: PO_Order_Specification_2026.pdf.exe\n\nPlease check the specifications in the PDF file and confirm back to us."
        }
    ]
}

# --- ROUTES ĐĂNG NHẬP / ĐĂNG KÝ / ĐĂNG XUẤT ---

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        user = next((u for u in db_users if u['username'] == username and u['password'] == password), None)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = user['role']
            return jsonify({"status": "success", "message": "Đăng nhập thành công!", "role": user['role']})
        else:
            return jsonify({"status": "error", "message": "Tên đăng nhập hoặc mật khẩu không chính xác!"}), 400

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        name = data.get('name', '').strip()
        password = data.get('password', '').strip()

        if not username or not name or not password:
            return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ thông tin!"}), 400

        if any(u['username'] == username for u in db_users):
            return jsonify({"status": "error", "message": "Tên đăng nhập đã tồn tại!"}), 400

        new_user = {
            "id": len(db_users) + 1,
            "username": username,
            "password": password,
            "name": name,
            "role": "user",
            "score": 0,
            "reports": 0,
            "traps": 0,
            "risk_level": "Chưa đánh giá",
            "pre_score": 0,
            "post_score": 0
        }
        db_users.append(new_user)
        return jsonify({"status": "success", "message": "Đăng ký thành công! Vui lòng đăng nhập."})

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# --- TRANG CHÍNH & API HỆ THỐNG ---

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/get-current-user', methods=['GET'])
@login_required
def get_current_user():
    user = next((u for u in db_users if u['id'] == session.get('user_id')), None)
    if user:
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "message": "Không tìm thấy người dùng"}), 404

@app.route('/api/submit-pre-test', methods=['POST'])
@login_required
def submit_pre_test():
    data = request.get_json()
    score = 0
    if data.get("q1") == "out_of_band": score += 25
    if data.get("q2") == "process": score += 25
    if data.get("q3") == "challenge": score += 25
    if data.get("q4") == "report": score += 25

    user = next((u for u in db_users if u['id'] == session.get('user_id')), None)
    if user:
        user['pre_score'] = score
        user['score'] = score
        if data.get("user_name"):
            user['name'] = data.get("user_name")
            session['name'] = user['name']

    return jsonify({"status": "success", "score": score})

@app.route('/api/get-role-scenarios/<role_id>', methods=['GET'])
@login_required
def get_role_scenarios(role_id):
    scenarios = ROLE_SCENARIOS.get(role_id, ROLE_SCENARIOS["accountant"])
    return jsonify({"status": "success", "role": role_id, "scenarios": scenarios})

@app.route('/api/analyze-threat', methods=['POST'])
@login_required
def analyze_threat():
    data = request.get_json()
    text = data.get("text", "")

    keywords_phishing = ["chuyển tiền", "mật khẩu", "otp", "ngân hàng", "gấp", "click", "m&a", "cập nhật", "truy cập", "hạn chót", "phong tỏa"]
    keywords_deepfake = ["video call", "sân bay", "sóng yếu", "chủ tịch", "cfo", "giám đốc", "thanh tra", "giọng nói"]

    score_phishing = sum(1 for k in keywords_phishing if re.search(k, text, re.IGNORECASE))
    score_deepfake = sum(1 for k in keywords_deepfake if re.search(k, text, re.IGNORECASE))

    risk = "An toàn"
    reasons = []

    if score_phishing >= 2 or score_deepfake >= 2:
        risk = "Nguy cơ Cao (Cảnh báo Lừa đảo / Deepfake)"
        if score_phishing >= 2:
            reasons.append("Phát hiện từ khóa hối thúc tài chính & liên kết nghi vấn Phishing.")
        if score_deepfake >= 2:
            reasons.append("Phát hiện ngữ cảnh giả mạo danh tính/cuộc gọi khẩn (Deepfake indicator).")
    elif score_phishing == 1 or score_deepfake == 1:
        risk = "Nguy cơ Trung bình"
        reasons.append("Có chứa một số từ ngữ nhạy cảm cần xác minh lại.")

    return jsonify({
        "status": "success",
        "risk_level": risk,
        "reasons": reasons,
        "recommendation": "Yêu cầu thực hiện xác minh qua Kênh thứ 2 (Out-of-band) trước khi thực hiện giao dịch!"
    })

@app.route('/api/get-leaderboard', methods=['GET'])
@login_required
def get_leaderboard():
    return jsonify({"status": "success", "all_users": db_users})

@app.route('/api/submit-post-test', methods=['POST'])
@login_required
def submit_post_test():
    data = request.get_json()
    post_score = 0
    if data.get("q1") == "out_of_band": post_score += 25
    if data.get("q2") == "process": post_score += 25
    if data.get("q3") == "challenge": post_score += 25
    if data.get("q4") == "report": post_score += 25

    user = next((u for u in db_users if u['id'] == session.get('user_id')), None)
    pre_score = 0
    growth = 0
    unlocked_badges = []

    if user:
        pre_score = user.get('pre_score', 0)
        user['post_score'] = post_score
        user['score'] = max(post_score, user.get('score', 0))
        growth = post_score - pre_score
        if user['score'] >= 75:
            unlocked_badges.append("Bậc Thầy Nhận Thức An Ninh Mạng")

    return jsonify({
        "status": "success",
        "pre_score": pre_score,
        "post_score": post_score,
        "growth": growth,
        "game_score": user['score'] if user else post_score,
        "unlocked_badges": unlocked_badges
    })

# --- API ADMIN (CRUD USER & ANALYTICS) ---

@app.route('/api/get-admin-analytics', methods=['GET'])
@admin_required
def get_admin_analytics():
    total_pre = sum([u.get("pre_score", 0) for u in db_users])
    total_post = sum([u.get("post_score", 0) for u in db_users])
    avg_pre = round(total_pre / max(len(db_users), 1), 1)
    avg_post = round(total_post / max(len(db_users), 1), 1)

    total_traps = sum([u.get("traps", 0) for u in db_users])
    total_reports = sum([u.get("reports", 0) for u in db_users])

    high_risk_users = [u for u in db_users if u.get("traps", 0) > 1 or u.get("score", 0) < 50]

    return jsonify({
        "status": "success",
        "avg_pre": avg_pre,
        "avg_post": avg_post,
        "total_traps": total_traps,
        "total_reports": total_reports,
        "high_risk_users": high_risk_users
    })

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    return jsonify({"status": "success", "users": db_users})

@app.route('/api/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user():
    data = request.get_json()
    username = data.get("username", "").strip()
    name = data.get("name", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "user")
    score = int(data.get("score", 0))
    traps = int(data.get("traps", 0))
    reports = int(data.get("reports", 0))
    risk_level = data.get("risk_level", "Thấp")

    if not username or not password or not name:
        return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ thông tin Tên đăng nhập, Mật khẩu và Họ tên!"}), 400

    if any(u['username'] == username for u in db_users):
        return jsonify({"status": "error", "message": "Tên đăng nhập đã tồn tại!"}), 400

    new_id = max([u['id'] for u in db_users], default=0) + 1
    new_user = {
        "id": new_id,
        "username": username,
        "password": password,
        "name": name,
        "role": role,
        "score": score,
        "reports": reports,
        "traps": traps,
        "risk_level": risk_level,
        "pre_score": score,
        "post_score": score
    }
    db_users.append(new_user)
    return jsonify({"status": "success", "message": "Thêm người dùng thành công!"})

@app.route('/api/admin/users/edit/<int:user_id>', methods=['PUT', 'POST'])
@admin_required
def admin_edit_user(user_id):
    data = request.get_json()
    user = next((u for u in db_users if u['id'] == user_id), None)
    if not user:
        return jsonify({"status": "error", "message": "Không tìm thấy người dùng!"}), 404

    user['name'] = data.get("name", user['name'])
    user['role'] = data.get("role", user['role'])
    user['score'] = int(data.get("score", user['score']))
    user['traps'] = int(data.get("traps", user['traps']))
    user['reports'] = int(data.get("reports", user['reports']))
    user['risk_level'] = data.get("risk_level", user['risk_level'])
    
    if data.get("password"):
        user['password'] = data.get("password")

    return jsonify({"status": "success", "message": "Cập nhật người dùng thành công!"})

@app.route('/api/admin/users/delete/<int:user_id>', methods=['DELETE', 'POST'])
@admin_required
def admin_delete_user(user_id):
    global db_users
    if user_id == session.get('user_id'):
        return jsonify({"status": "error", "message": "Không thể xóa tài khoản Admin đang đăng nhập!"}), 400

    db_users = [u for u in db_users if u['id'] != user_id]
    return jsonify({"status": "success", "message": "Đã xóa người dùng khỏi hệ thống!"})

# KHỞI CHẠY ỨNG DỤNG PYWEBVIEW / FLASK
def start_flask():
    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    webview.create_window(
        'CyberAware - Môi trường Giả lập & Nâng cao Nhận thức An ninh mạng 2026',
        'http://127.0.0.1:5000',
        width=1366,
        height=800,
        resizable=True
    )
    webview.start()