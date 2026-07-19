19/07/26
Sprint 3 phần lõi đã hoàn tất — ReAct loop chạy đúng: Thought → Action → Observation (tool thật, không bịa) → Thought → Final Answer, dừng đúng lúc, không rơi vào vòng lặp giả (trong trường hợp test thử)

ReAct prompting bắt buộc phải chặn LLM dừng lại ngay sau Action Input: {...} bằng stop sequence — nếu không, model (đặc biệt các model "chăm chỉ" như Gemini) có xu hướng tự hoàn thành luôn cả đoạn hội thoại tưởng tượng, bao gồm cả Observation giả

stop_sequences là bắt buộc khi tự cài ReAct loop — thiếu nó, Agent trông như hoạt động nhưng thực chất toàn bộ Observation là ảo giác của LLM.


multi-tool action: 
LLM có thể bịa toàn bộ chuỗi Action→kết quả→Final Answer trong 1 lần sinh mà không cần vi phạm stop_sequences cụ thể nào — cần parse dựa theo vị trí marker xuất hiện trước/sau trong text, không dựa theo 'có tồn tại hay không
Đây là dạng "reward hacking" tự nhiên của LLM: model học được cách "trông như đã hoàn thành nhiệm vụ" (viết Final Answer) mà không cần thực sự chờ kết quả thật — nếu không kiểm tra kỹ, đồ án sẽ trông như chạy đúng (có câu trả lời, có vẻ hợp lý) nhưng bản chất Agent không hề dùng tool thật, phá vỡ hoàn toàn ý nghĩa của kiến trúc ReAct + Tool Calling. Đây chính xác là điều khiến việc so sánh RAG-only vs Agent+RAG (đóng góp học thuật) có ý nghĩa: nếu Agent âm thầm "giả vờ" dùng tool, kết quả eval sẽ sai lệch nghiêm trọng.
