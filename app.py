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

# KỊCH BẢN CHÍNH
ROLE_SCENARIOS = {
    "accountant": [
        {
            "id": "acc_1",
            "type": "Phishing",
            "title": "Cảnh báo Quyết toán Thuế TNCN & Hoàn trả Chi phí Dư Q2/2026 (Portal Kế toán)",
            "desc": "Email giả mạo Phòng Tài chính - Kế toán thông báo khoản hoàn trả chi phí thâm niên & thuế TNCN, thúc giục đăng nhập Cổng đối soát trước 17h00 để nhận tiền.",
            "trap_reason": "Bạn đã bị dụ bấm vào trang Phishing cướp tài khoản SSO/Email công ty! Kẻ tấn công lợi dụng tâm lý tò mò về quyền lợi tài chính cá nhân và tạo áp lực thời gian (trước 17h00) để bạn đăng nhập mà không đối soát nội bộ.",
            "content": "Kính gửi Chị Kế toán trưởng và Ban Tài chính - Kế toán,\n\nBộ phận Kế toán Tổng hợp vừa hoàn tất công tác đối soát chi phí hoạt động và quỹ lương Q2/2026. Qua kiểm tra dữ liệu đóng thuế TNCN và các khoản phụ cấp hoàn ứng thâm niên, hệ thống ghi nhận tài khoản của Anh/Chị nằm trong danh sách được hoàn trả khoản chi phí dư (Mức hoàn trả dao động từ 2.400.000 VNĐ đến 6.800.000 VNĐ tùy theo thâm niên công tác).\n\nĐể Bộ phận Thủ quỹ tiến hành giải ngân lệnh chuyển khoản tự động trong đợt quyết toán chiều nay, Anh/Chị vui lòng kiểm tra bảng kê chi tiết và xác nhận số tài khoản thụ hưởng theo quy trình:\n1. Truy cập vào Cổng Đối soát Tài chính Doanh nghiệp: http://ketoan-quyettoan-company-finance-portal.net/tax-refund-2026\n2. Đăng nhập bằng Email Công ty để xác thực mã định danh nhân sự.\n3. Kiểm tra số tiền hoàn trả và bấm \"Xác nhận giải ngân\".\n\n(Lưu ý: Các trường hợp không xác nhận trước 17h00 hôm nay sẽ phải chờ chuyển sang đợt quyết toán của Quý IV).",
            "correct_action": "Không truy cập liên kết lạ. Kiểm tra lại địa chỉ gửi, xác minh trực tiếp với bộ phận Kế toán tổng hợp/Nhân sự nội bộ."
        },
        {
            "id": "acc_2",
            "type": "Deepfake Video Call",
            "title": "Cuộc gọi Video Deepfake từ Con Gái: Nhập Viện Khẩn Cấp Cần Chuyển Tiền Gấp",
            "desc": "Mẹ nhận được cuộc gọi video ngắn từ tài khoản con gái thông báo đang nhập viện khẩn cấp và cần chuyển ngay 1 triệu đồng, dặn mẹ không gọi lại ngay.",
            "video_url": "/statics/videos/test1.mp4",
            "duration": "00:13",
            "video_script": "Con chào mẹ. Con là Trang đây. Mẹ ơi hiện tại con đang nhập viện. Mẹ có thể chuyển tiền cho con một triệu được không? Mẹ gọi sau cho con nha?",
            "subtle_clues": [
                "Tần suất chớp mắt của con gái ít bất thường, ánh mắt thiếu tự nhiên.",
                "Vùng da quanh viền cổ, tai và đường nét khuôn mặt bị mờ nhòe khi nhân vật di chuyển.",
                "Giọng nói có âm thanh kim loại nhẹ, bị đứt đoạn và lệch pha so với khẩu hình môi.",
                "Đối phương chủ động hối thúc chuyển tiền và dặn 'gọi sau' để tránh bị phát hiện qua cuộc gọi thoại trực tiếp."
            ],
            "correct_action": "Bình tĩnh cúp máy ngay lập tức, tuyệt đối không chuyển tiền. Gọi trực tiếp lại cho con gái qua số điện thoại di động thông thường (hoặc gọi cho bạn bè/người thân đi cùng con) để xác thực thông tin.",
            "trap_reason": "Bạn đã sập bẫy Deepfake Video Call mạo danh Người thân! Kẻ gian dùng AI thu thập hình ảnh, video và giọng nói của con gái trên mạng xã hội để cắt ghép, tạo áp lực tâm lý hoảng loạn nhằm chiếm đoạt tài sản."
        },
        {
            "id": "acc_3",
            "type": "Social Engineering",
            "title": "Giả danh Cán bộ Thanh tra Thuế Cảnh báo Lỗi Sổ sách & Đe dọa Phong tỏa Tài khoản Doanh nghiệp",
            "desc": "Kẻ gian đóng vai Cán bộ Thuế gọi điện và gửi văn bản giả tạo áp lực phong tỏa tài khoản ngân hàng công ty trong 24h nếu không làm thủ tục ký quỹ tạm thời.",
            "trap_reason": "Bạn đã bị thao túng tâm lý bởi chiêu trò mạo danh Cơ quan Công quyền! Cơ quan Thuế không bao giờ làm việc qua điện thoại yêu cầu chuyển tiền vào tài khoản cá nhân hay 'tài khoản ký quỹ tạm thời' để hoãn lệnh phong tỏa.",
            "content": "\"Chào chị Kế toán trưởng, tôi là Nguyễn Văn Nam - Cán bộ Chi cục Thuế TP. Qua đối soát dữ liệu hóa đơn điện tử Q2/2026, hệ thống phát hiện doanh nghiệp mình bị lệch sổ sách VAT và chi phí đầu vào lên tới 1.2 tỷ VNĐ. Hiện tại Đoàn Thanh tra đã lập hồ sơ vi phạm và dự kiến ban hành quyết định phong tỏa toàn bộ tài khoản ngân hàng doanh nghiệp trong 24h tới.\n\nTuy nhiên, để tạo điều kiện cho doanh nghiệp giải trình và bổ sung chứng từ mà không làm gián đoạn dòng tiền vận hành, chị cần làm thủ tục đóng tiền ký quỹ tạm thời 150.000.000 VNĐ vào Tài khoản Tạm thu của Thanh tra Thuế trước 11h30 sáng nay. Tôi sẽ gửi văn bản dấu đỏ qua Zalo cho chị kiểm tra ngay!\""
        },
        {
            "id": "acc_4",
            "type": "Spear Phishing & Vishing",
            "title": "Kịch bản Kép: Email Hóa đơn Logistics Sai lệch kết hợp Cuộc gọi Giả danh Kế toán trưởng Đối tác",
            "desc": "Kẻ tấn công gửi Email Phishing chứa link Hóa đơn điện tử điều chỉnh, sau đó gọi điện (Vishing) đóng vai Kế toán đối tác hối thúc Kế toán truy cập xác nhận.",
            "trap_reason": "Bạn đã sập bẫy Tấn công Đa kênh (Spear Phishing + Vishing)! Kẻ gian kết hợp Email nhắm mục tiêu chính xác kèm cuộc gọi hối thúc nhằm làm giảm sự cảnh giác và xóa bỏ nghi ngờ của nạn nhân.",
            "content": "✉️ EMAIL: [GẤP] Biên bản nghiệm thu & Yêu cầu điều chỉnh Hóa đơn điện tử lô hàng Logistics #HD2026-88.\nNgười gửi: Đỗ Thùy Linh - Kế toán trưởng <linh.dt@doitac-logistics-corp.com>\nNội dung: Kính gửi Bộ phận Kế toán, lô hàng đợt 2 đã bàn giao xong nhưng mã số thuế và bảng đối soát của Quý công ty đang bị lệch. Nhờ Anh/Chị truy cập Cổng Hóa đơn Điện tử tại http://doitac-logistics-corp.com/invoice-check để xem biên bản và xác nhận bảng kê điều chỉnh trước 16h00 để bên tôi xuất lại VAT chuẩn.\n\n📞 VISHING (CUỘC GỌI): \"Alo em ơi, chị Linh Kế toán trưởng bên Logistics đợt hàng #HD2026-88 đây. Chị vừa gửi email hóa đơn điều chỉnh đấy, em bấm vào link xác nhận gấp giúp chị để bên chị kịp xuất lại VAT trong chiều nay nhé, sếp bên chị đang hối dữ lắm!\""
        }
    ],

    "hr": [
        {
            "id": "hr_1",
            "type": "Phishing",
            "title": "Email Giả mạo Công đoàn: Mở đăng ký Gói Phúc lợi Kỳ nghỉ 5 Sao & Quỹ Tiết kiệm Sinh lời 2026",
            "desc": "Email giả mạo Công đoàn dụ nhân viên HR đăng nhập tài khoản Microsoft 365 để nhận Voucher du lịch 15 triệu và đăng ký Quỹ tiết kiệm lãi suất 12%/năm.",
            "trap_reason": "Bạn đã bị đánh cắp tài khoản Email Doanh nghiệp! Cổng đăng nhập mạo danh congdoan-phucloi-company-portal.com thu thập Tên đăng nhập & Mật khẩu của bạn thông qua bẫy lợi ích kinh tế.",
            "content": "Kính gửi Toàn thể Cán bộ Nhân viên & Bộ phận HR,\n\nNhằm tri ân những đóng góp của cán bộ nhân viên, Ban Chấp hành Công đoàn phối hợp cùng Ban Giám đốc chính thức phát động Chương trình Phúc lợi Đặc biệt 2026 với 2 hạng mục ưu đãi lớn:\n1. Tặng Voucher Hợp đồng Kỳ nghỉ 5 Sao (Trị giá 15.000.000 VNĐ): Áp dụng cho gia đình 4 người tại các khu nghỉ dưỡng thuộc hệ thống đối tác toàn quốc.\n2. Quỹ Hợp tác Tiết kiệm Sinh lời Nội bộ: Nhân viên đăng ký gửi tích lũy phúc lợi từ 1.000.000 VNĐ sẽ nhận ngay tiền mặt thưởng 500.000 VNĐ và hưởng lãi suất ưu đãi nội bộ 12%/năm.\n\nDo số lượng suất quà tặng có hạn (chỉ dành cho 50 nhân viên đăng ký sớm nhất), kính mời Anh/Chị nhanh chóng đăng ký trực tuyến:\n👉 Truy cập Cổng Phúc lợi: http://congdoan-phucloi-company-portal.com/register-benefit\n👉 Đăng nhập tài khoản Email Công ty để xác nhận mã định danh nhân viên.",
            "correct_action": "Báo cáo Email Phishing cho bộ phận IT Security. Không đăng nhập thông tin công ty vào các trang web ngoài hệ thống."
        },
        {
            "id": "hr_2",
            "type": "Deepfake Video Call",
            "title": "Cuộc gọi Video Deepfake từ Con Trai: Xin Tiền Đóng Học Phí Gấp",
            "desc": "Mẹ nhận được cuộc gọi video ngắn từ tài khoản con trai thông báo sắp đến hạn đóng học phí và xin gấp 10 triệu đồng, dặn mẹ gọi lại sau.",
            "video_url": "/statics/videos/test2.mp4",
            "duration": "00:13",
            "video_script": "Con chào mẹ, Con là Phúc con sắp đóng học phí, mẹ cho con xin 10 triệu để đóng học phí nhé, Mẹ gọi lại con sau nha?",
            "subtle_clues": [
                "Khẩu hình miệng không khớp hoàn toàn với âm thanh thoại.",
                "Cảnh nền phía sau bị đơ (tĩnh) hoặc nhòe bất thường.",
                "Tốc độ nói nhanh đột biến, cố tình ngắt kết nối sớm và dặn 'gọi sau' để tránh bị xác minh qua cuộc gọi kéo dài."
            ],
            "correct_action": "Bình tĩnh cúp máy, tuyệt đối không chuyển tiền ngay. Chủ động gọi lại cho con trai qua số di động thông thường hoặc liên hệ nhà trường/bạn bè cùng lớp để xác thực thông tin đóng học phí.",
            "trap_reason": "Bạn đã sập bẫy Deepfake Video Call mạo danh Người thân! Kẻ gian dùng AI thu thập hình ảnh và giọng nói của con trai trên mạng xã hội để dựng video giả mạo, lợi dụng tâm lý lo lắng cho việc học của con để lừa đảo chiếm đoạt tài sản."
        },
        {
            "id": "hr_3",
            "type": "Social Engineering",
            "title": "Bẫy File CV Mã độc Ransomware: Ứng tuyển Vị trí Cấp cao Yêu cầu 'Enable Macro' để xem Bảng lương",
            "desc": "Email ứng tuyển vị trí Giám đốc Kinh doanh đính kèm file .zip có mật khẩu, yêu cầu HR mở file Word và bấm Enable Content để giải mã hồ sơ bảo mật.",
            "trap_reason": "Bạn đã kích hoạt Mã độc Mã hóa Dữ liệu (Ransomware)! Kẻ tấn công dùng file nén có mật khẩu để vượt qua hệ thống Quét Virus tự động. Thao tác 'Enable Content' chính là chạy Script độc hại mã hóa máy tính.",
            "content": "Kính gửi Ban Giám đốc và Bộ phận Nhân sự (HR),\n\nTôi xin gửi Hồ sơ ứng tuyển vị trí Giám đốc Kinh doanh theo thông tin tuyển dụng của Công ty. Tôi có hơn 10 năm kinh nghiệm điều hành tại các Tập đoàn đa quốc gia.\n\nDo thông tin về Bảng lương cũ, Danh sách Dự án và Cam kết Doanh số có tính chất bảo mật riêng tư, tôi đã nén toàn bộ tài liệu vào file đính kèm dưới dạng mã hóa:\n📁 File đính kèm: Ho_So_Nang_Luc_Ung_Vien_NguyenVanHung.zip (Mật khẩu giải nén: 123456)\n\nVui lòng giải nén, mở file Word và bấm \"Enable Editing / Enable Content\" trên thanh công cụ để hệ thống tự động giải mã văn bản. Rất mong nhận được phản hồi lịch phỏng vấn."
        },
        {
            "id": "hr_4",
            "type": "Spear Phishing & Vishing",
            "title": "Kịch bản Kép: Email Hồ sơ Ứng viên Senior từ TGĐ kết hợp Cuộc gọi Giả mạo Headhunter hối thúc",
            "desc": "Email chứa link Cổng Đánh giá Ứng viên giả mạo (SSO Phishing), đi kèm cuộc gọi từ Headhunter thúc giục HR mở hồ sơ gấp để kịp lịch họp với TGĐ.",
            "trap_reason": "Bạn đã sập bẫy Tấn công Đa kênh nhắm mục tiêu (Spear Phishing + Vishing)! Kẻ gian đánh trúng tâm lý áp lực KPI tuyển dụng và sự e sợ chỉ đạo từ Ban Giám đốc.",
            "content": "✉️ EMAIL: Tiêu đề: [HR-PRIORITY] Hồ sơ Trưởng phòng Kinh doanh Senior - Phạm Minh Tuấn (Ứng viên do TGĐ gửi trực tiếp).\nNgười gửi: Phạm Minh Tuấn <tuan.pm.headhunter@corporate-hrpool.com>\nNội dung: Kính gửi HR, tôi gửi hồ sơ theo trao đổi với anh Hoàng TGĐ. Hồ sơ năng lực và video thuyết trình đã được bảo mật trên Cổng Đánh giá Ứng viên Cấp cao. Vui lòng truy cập http://corporate-hrpool.com/candidate-tuan-pm và đăng nhập Email Công ty để xác thực thẩm quyền xem tài liệu.\n\n📞 VISHING (CUỘC GỌI): \"Chào em, anh Tuấn bên HR-Pool đây. Anh vừa gửi hồ sơ ứng viên Senior cho vị trí TGĐ giao đấy. Anh Hoàng TGĐ dặn kiểm tra gấp trong sáng nay để chiều anh ấy duyệt, em truy cập link xem rồi xếp lịch phỏng vấn giúp anh nhé!\""
        }
    ],

    "it": [
        {
            "id": "it_1",
            "type": "Phishing",
            "title": "Cảnh báo Giả mạo AWS Cloud: Chứng chỉ SSL & Server Core bị Hết hạn do Lỗi Billing",
            "desc": "Email mạo danh AWS Cloud Services gửi Cảnh báo khẩn cấp, yêu cầu IT Admin đăng nhập tài khoản Root để gia hạn API Key và cập nhật thẻ thanh toán.",
            "trap_reason": "Bạn đã nhập Master API Key / Credentials hệ thống Cloud lên tên miền giả mạo! Tên miền aws-console-verify.net là trang Phishing. Kẻ tấn công sẽ chiếm quyền điều khiển toàn bộ hạ tầng Cloud của tổ chức.",
            "content": "CRITICAL NOTICE: SSL Certificate & Wildcard DNS cho hệ thống Core Doanh nghiệp sẽ bị chấm dứt kết nối sau 2 giờ nữa do lỗi đồng bộ billing thẻ tín dụng thanh toán tự động.\n\nNếu không gia hạn kịp thời, toàn bộ dịch vụ Web, ERP và Database sẽ bị gián đoạn truy cập. Vui lòng truy cập ngay cổng quản trị hạ tầng khẩn cấp tại:\n👉 Link: http://aws-console-verify.net/root-login\n\nTiến hành đăng nhập tài khoản Root/Admin và cập nhật Master API Key để hệ thống tự động gia hạn chứng chỉ SSL khẩn cấp.",
            "correct_action": "Không bấm liên kết trong Email. Truy cập trực tiếp trang quản trị AWS qua Bookmark chính thức để kiểm tra trạng thái Billing."
        },
        {
            "id": "it_2",
            "type": "Deepfake Video Call",
            "title": "Cuộc gọi Video Deepfake từ Con Gái: Nhập Viện Khẩn Cấp Cần Chuyển Tiền Gấp",
            "desc": "Mẹ nhận được cuộc gọi video ngắn từ tài khoản con gái thông báo đang nhập viện khẩn cấp và cần chuyển ngay 1 triệu đồng, dặn mẹ gọi lại sau.",
            "video_url": "/statics/videos/test1.mp4",
            "duration": "00:13",
            "video_script": "Con chào mẹ. Con là Trang đây. Mẹ ơi hiện tại con đang nhập viện. Mẹ có thể chuyển tiền cho con một triệu được không? Mẹ gọi sau cho con nha?",
            "subtle_clues": [
                "Hình ảnh bị giật nhẹ mỗi khi nhân vật xua tay hoặc di chuyển đầu.",
                "Ánh sáng trên khuôn mặt không khớp tự nhiên với môi trường xung quanh.",
                "Tốc độ truyền tải thoại bị trễ bất thường so với cử động miệng.",
                "Chủ động dặn 'mẹ gọi sau cho con nha' để cắt ngắn cuộc gọi, tránh bị phát hiện các sơ hở tiếp theo."
            ],
            "correct_action": "Bình tĩnh cúp máy ngay lập tức, tuyệt đối không chuyển tiền. Gọi lại trực tiếp cho con gái qua số điện thoại di động chính hoặc liên hệ với bạn bè, người thân xung quanh con để xác thực thông tin.",
            "trap_reason": "Bạn đã sập bẫy Deepfake Video Call mạo danh Người thân! Kẻ gian sử dụng AI thu thập hình ảnh và giọng nói của con gái trên mạng xã hội để dựng video giả mạo, lợi dụng tâm lý hoảng loạn, lo lắng cho con cái để lừa đảo chiếm đoạt tài sản."
        },
        {
            "id": "it_3",
            "type": "Social Engineering",
            "title": "Tấn công Phishing Đánh cắp Personal Access Token (PAT) Kho Mã nguồn GitLab/GitHub",
            "desc": "Cảnh báo mạo danh GitLab/GitHub báo SSH Key bị rò rỉ, dụ Developer đăng nhập Cổng Login giả để reset Token và bảo vệ Repository.",
            "trap_reason": "Bạn đã cung cấp Token truy cập và Credential kho mã nguồn tổ chức! Kẻ tấn công có thể chèn mã độc vào Source Code (Supply Chain Attack) hoặc đánh cắp toàn bộ sở hữu trí tuệ công ty.",
            "content": "[GitLab Internal Alert]: Phát hiện Personal Access Token (PAT) và SSH Key của tài khoản Developer của bạn vừa bị rò rỉ trên một Repository công khai trên GitHub.\n\nĐể đảm bảo an toàn cho toàn bộ Source Code dự án Q3, hệ thống đã tạm thời khóa quyền Push code của tài khoản này. Vui lòng truy cập ngay cổng xác thực an ninh nội bộ để hủy Token cũ và cấp lại Access Token mới:\n👉 Link: http://gitlab-internal-auth.com/reset-token\n\n(Hạn chót xử lý trong vòng 12 giờ trước khi tài khoản bị khóa vĩnh viễn)."
        },
        {
            "id": "it_4",
            "type": "Spear Phishing & Vishing",
            "title": "Kịch bản Kép: Email Cảnh báo Lỗi VPN Doanh nghiệp kết hợp Cuộc gọi từ IT Helpdesk Giả mạo",
            "desc": "Email yêu cầu cập nhật Patch bảo mật cho VPN Client đính kèm link tải mã độc, kết hợp cuộc gọi vishing giả dạng Chuyên gia IT Network hỗ trợ cài đặt.",
            "trap_reason": "Bạn đã sập bẫy Kỹ thuật xã hội nhắm mục tiêu vào Khối Kỹ thuật (Spear Phishing + Vishing)! Kẻ gian giả danh Đồng nghiệp IT Network để tạo lòng tin và dẫn dụ bạn thực thi File mã độc.",
            "content": "✉️ EMAIL: Tiêu đề: [IT-NOTICE] Cập nhật Patch Bảo mật Khẩn cấp cho Fortinet VPN Client phòng chống tấn công DDoS.\nNgười gửi: Admin Helpdesk <admin-helpdesk@company-cloud-security.com>\nNội dung: Hệ thống đang bị tấn công DDoS qua cổng VPN cũ. Yêu cầu toàn bộ nhân sự kỹ thuật tải bản Patch cập nhật tại http://fortinet-corp-update.net/vpn-patch và chạy file setup.exe.\n\n📞 VISHING (CUỘC GỌI): \"Alo anh, em bên Đội An ninh mạng IT Network đây. Hộp thư công ty đang bị tấn công DDoS qua cổng VPN cũ, em vừa gửi link Patch qua email đấy. Anh bấm tải file .exe về chạy luôn giúp em để bảo vệ máy tính và giữ kết nối server nhé!\""
        }
    ],

    "sales": [
        {
            "id": "sales_1",
            "type": "Phishing",
            "title": "Thư Mời Thầu & Yêu cầu Báo Giá Dự án Triển khai Phần mềm 3.2 Tỷ (Microsoft SharePoint)",
            "desc": "Email từ Khách hàng lớn gửi link SharePoint yêu cầu đăng nhập tài khoản Email Doanh nghiệp để tải Hồ sơ Thầu bảo mật.",
            "trap_reason": "Bạn đã nhập thông tin tài khoản doanh nghiệp vào trang web Phishing giả mạo SharePoint! Kẻ tấn công lợi dụng tâm lý hám lời và áp lực chỉ tiêu doanh số từ các hợp đồng giá trị cao.",
            "content": "Kính gửi Phòng Kinh doanh & Ban Giám đốc,\n\nChúng tôi đại diện cho Tập đoàn SunGroup trân trọng mời Quý công ty tham gia chào giá gói thầu tư vấn triển khai hạ tầng & phần mềm quản trị cho dự án mới của chúng tôi (Tổng giá trị dự kiến 3.2 Tỷ VNĐ).\n\nDo yêu cầu bảo mật nghiêm ngặt của Hồ sơ Mời thầu (RFP), toàn bộ File Báo cáo Kỹ thuật, Bảng Tiêu chuẩn và Dự thảo Hợp đồng đã được tải lên Cổng lưu trữ SharePoint Doanh nghiệp:\n👉 Link: http://partner-corp-group.net/rfp-2026-sungroup\n\nVui lòng Đăng nhập bằng Tài khoản Microsoft / Email Doanh nghiệp của bạn để xác thực quyền xem và tải Hồ sơ Mời thầu (Hạn nộp báo giá: Trước 12:00 ngày mai).",
            "correct_action": "Không đăng nhập tài khoản công ty trên các liên kết SharePoint lạ. Xác minh lại với bộ phận Mua hàng/Đầu mối chính thức của đối tác."
        },
        {
            "id": "sales_2",
            "type": "Deepfake Video Call",
            "title": "Cuộc gọi Video Deepfake từ Con Trai: Xin Tiền Đóng Học Phí Gấp",
            "desc": "Mẹ nhận được cuộc gọi video ngắn từ tài khoản con trai thông báo sắp đến hạn đóng học phí và xin gấp 10 triệu đồng, dặn mẹ gọi lại sau.",
            "video_url": "/statics/videos/test2.mp4",
            "duration": "00:13",
            "video_script": "Con chào mẹ, Con là phúc con sắp đóng học phí, mẹ cho con xin 10 triệu để đóng học phí nhé, Mẹ gọi lại con sau nha?",
            "subtle_clues": [
                "Cơ mặt chuyển động thiếu tự nhiên khi nhân vật nói nhanh.",
                "Ánh mắt nhìn chệch khỏi ống kính camera liên tục, thiếu tự nhiên.",
                "Âm thanh cuộc gọi chập chờn, bị đứt đoạn ở các từ cuối câu.",
                "Cố tình tạo áp lực thời gian và dặn 'Mẹ gọi lại con sau nha' để chủ động cắt ngang cuộc gọi, tránh bị phát hiện các điểm bất thường."
            ],
            "correct_action": "Bình tĩnh cúp máy ngay lập tức, tuyệt đối không chuyển tiền ngay. Gọi điện trực tiếp lại cho con trai qua số di động thông thường hoặc liên hệ nhà trường/bạn bè để xác thực lại thông tin đóng học phí.",
            "trap_reason": "Bạn đã sập bẫy Deepfake Video Call mạo danh Người thân! Kẻ gian lợi dụng công nghệ AI để dựng video giả mạo con trai, đánh vào tâm lý lo lắng cho việc học của con cái nhằm chiếm đoạt tài sản."
        },
        {
            "id": "sales_3",
            "type": "Social Engineering",
            "title": "Xác nhận Đơn đặt hàng Xuất khẩu Khẩn (Gửi file đính kèm Double-Extension PO_Order_Specification.pdf.exe)",
            "desc": "Khách hàng nước ngoài gửi file Purchase_Order_2026.pdf.exe yêu cầu Sales mở xem số lượng và thông số kỹ thuật gấp để kịp đóng container.",
            "trap_reason": "Bạn đã bị cài Trojan / Spyware theo dõi bàn phím! Kẻ gian thực hiện kịch bản đổi đuôi file double-extension (.pdf.exe) để lừa người dùng bấm vào chạy file thực thi độc hại.",
            "content": "Dear Sales Team,\n\nPlease find attached our official Purchase Order (PO) and Technical Specifications for Q3 shipment. We need 5,000 units delivered by next month.\n\n📁 Attached File: PO_Order_Specification_2026.pdf.exe\n\nPlease check the specifications in the PDF file and confirm back to us urgently so we can arrange the deposit transfer today."
        },
        {
            "id": "sales_4",
            "type": "Spear Phishing & Vishing",
            "title": "Kịch bản Kép: Email Mời Tham gia Sàn B2B Đối tác Quốc tế kết hợp Gọi điện Giả danh Trưởng phòng Mua hàng đối tác",
            "desc": "Email gửi link đăng nhập hệ thống B2B nhận đơn hàng lớn, đi kèm cuộc gọi thúc giục từ Trưởng phòng Mua hàng đối tác yêu cầu xác nhận tài khoản.",
            "trap_reason": "Bạn đã sập bẫy Tấn công Đa kênh nhắm vào mục tiêu Doanh số (Spear Phishing + Vishing)! Kẻ gian lợi dụng tâm lý muốn chốt đơn nhanh của nhân viên Sales để lấy thông tin đăng nhập.",
            "content": "✉️ EMAIL: Tiêu đề: [B2B-OPPORTUNITY] Mời xác nhận thông tin Nhà cung cấp cấp 1 cho Dự án Khách sạn 5 sao.\nNgười gửi: Nguyễn Văn Nam - Trưởng phòng Mua hàng <nam.nv@b2b-procurement-partner.com>\nNội dung: Trân trọng mời Quý công ty tham gia chuỗi cung ứng. Vui lòng đăng nhập cổng B2B tại http://b2b-procurement-partner.com/vendor-login bằng Email Doanh nghiệp để hoàn tất hồ sơ năng lực.\n\n📞 VISHING (CUỘC GỌI): \"Alo em, anh Nam Trưởng phòng Mua hàng đây. Anh vừa gửi mail mời bên em làm nhà cung cấp đấy. Bấm vào link đăng nhập xác nhận thông tin doanh nghiệp gấp giúp anh để anh trình Giám đốc duyệt hợp đồng trong chiều nay nhé!\""
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