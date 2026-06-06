# So sánh với nghiên cứu arXiv:2604.26674

## Bối cảnh
Nghiên cứu *Reproducible Automated Program Repair Is Hard -- Experiences With the Defects4J Dataset* (Krafczyk & Schmid, 2026) chỉ ra rằng việc sử dụng tập dữ liệu Defects4J cho các nghiên cứu sửa lỗi tự động (APR) gặp nhiều vấn đề về tính tái lập, với khoảng 21.6% lỗi không phù hợp cho APR nghiêm ngặt.

## Điểm khác biệt và giá trị đóng góp của chúng ta
Thay vì cố gắng sửa lỗi trực tiếp trên Defects4J (như nghiên cứu gốc), dự án này sử dụng Defects4J làm **benchmark cho thuật toán tối ưu hóa test-selection** (Quantum-Inspired Evolutionary Algorithm - QIEA).

| Đặc điểm | arXiv:2604.26674 | Dự án Quantum Testing |
| :--- | :--- | :--- |
| **Trọng tâm** | Đánh giá tính tái lập APR | Tối ưu hóa chọn lọc test suite |
| **Phương pháp** | Phân tích thực nghiệm (APR) | Tối ưu hóa tổ hợp (QIEA) |
| **Defects4J** | Dùng để phân tích lỗi/sửa lỗi | Dùng để harvest test coverage matrix |
| **Giá trị** | Chỉ ra hạn chế của dataset | Chứng minh QIEA hiệu quả hơn Random/Greedy |

## Kết quả đạt được
Trên subset thực tế của Defects4J (Lang-1b), QIEA đã chứng minh:
1. **Full Coverage Reliability**: Đạt 100% coverage rate trong 30/30 seeds, trong khi Random Search đạt 0%.
2. **Efficiency**: Giữ nguyên coverage nhưng giảm thiểu số lượng test cần chọn so với các baseline.
3. **Reproducibility**: Cung cấp pipeline benchmark tự động, cho phép chạy lại các thực nghiệm với các seed khác nhau, khắc phục điểm yếu "reproducibility is hard" mà nghiên cứu gốc nhắc tới.

Tóm lại, dự án này đóng góp công cụ benchmark-driven để đánh giá các thuật toán tối ưu test suite trên dữ liệu thực tế, chứ không chỉ là giả lập.
