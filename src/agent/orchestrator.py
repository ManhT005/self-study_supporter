import ast
import json
import re
from src.llm.llm_adapter import LLMAdapter
from src.agent.state import AgentState
from src.agent.prompt_templates import build_react_system_prompt
from src.agent.tools.base import BaseTool


# 1. Gửi system_prompt + câu hỏi cho LLM
# 2. LLM trả về text dạng: "Thought: ...\nAction: ...\nAction Input: {...}"
# 3. Parse text đó ra: có Action không, hay đã có Final Answer?
#    - Có Action -> gọi đúng tool tương ứng -> lấy Observation -> nối vào scratchpad -> quay lại bước 1 (LLM thấy cả lịch sử cũ + Observation mới)
#    - Có Final Answer -> dừng vòng lặp, trả kết quả
# 4. Lặp tối đa `max_iterations` lần, tránh vòng lặp vô hạn



def _parse_action_input(raw: str) -> dict | None:
    """
    Thử parse JSON chuẩn trước; nếu model sinh kiểu Python dict (nháy đơn),
    fallback sang ast.literal_eval — an toàn hơn eval() vì chỉ chấp nhận
    literal (dict/list/str/số), không thực thi được code tùy ý.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return None

class ReActOrchestrator:
    def __init__(self, llm: LLMAdapter, tools: list[BaseTool]):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.system_prompt = build_react_system_prompt(tools)

    def parse_llm_output(self, text: str) -> dict:

        """

                      text
                        │
                        ▼
                Parse Thought
                        │
                        ▼
            Có Final Answer không?
                    │          │
                Có          Không
                    │            │
                    ▼            ▼
            return final   Có Action + JSON?
                                │        │
                            Có       Không
                                │        │
                                ▼        ▼
                    return action   invalid

        Parse text tự do từ LLM thành 1 trong 2 dạng:
        - {"type": "action", "thought": str, "action": str, "action_input": dict}
        - {"type": "final_answer", "thought": str, "final_answer": str}
        - {"type": "invalid", "raw": str}  <- khi không parse được (LLM trả sai định dạng)

        TODO: Viết bằng regex. Gợi ý các pattern cần dùng:
        - Thought:   r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|$)"  (dùng re.DOTALL)
        - Action:    r"Action:\s*(.+?)\n"
        - Action Input: r"Action Input:\s*(\{.*\})"  (dùng re.DOTALL, vì JSON có thể nhiều dòng)
        - Final Answer: r"Final Answer:\s*(.+)"  (dùng re.DOTALL, lấy tới hết chuỗi)

        Thứ tự kiểm tra:
        1. Nếu text có "Final Answer:" -> ưu tiên parse thành final_answer (bỏ qua Action nếu có, vì LLM có thể
           lỡ tay in cả 2, Final Answer luôn được ưu tiên là kết thúc).
        2. Nếu không có Final Answer nhưng có Action + Action Input -> parse thành action.
           Nhớ json.loads() cho Action Input, bọc try/except vì LLM có thể sinh JSON không hợp lệ
           (ví dụ dùng dấu nháy đơn thay vì nháy kép) -> nếu lỗi, trả về type "invalid".
        3. Nếu không khớp cả 2 -> trả về type "invalid".
        """
        # 1. Parse Thought (nếu có)
        thought = ""
        thought_match = re.search(
            r"Thought:?\s*(.+?)(?=\n[Aa]ction:|\nFinal Answer:|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        action_pos = text.find("Action:")
        final_pos = text.find("Final Answer:")

        # Marker nào xuất hiện TRƯỚC trong text mới là cái thật sự đáng tin.
        # Nếu Action xuất hiện trước Final Answer -> LLM đã cố tự bịa tiếp sau khi
        # gọi Action -> BẮT BUỘC coi đây là action thật, bỏ qua toàn bộ phần bịa phía sau.
        action_comes_first = action_pos != -1 and (final_pos == -1 or action_pos < final_pos)

        if action_comes_first:
            segment = text[action_pos:]
            action_match = re.search(r"Action:\s*(.+?)\n", segment)
            input_match = re.search(r"Action Input:\s*(\{.*?\})", segment, re.DOTALL)

            if action_match and input_match:
                action_input = _parse_action_input(input_match.group(1))
                if action_input is None:
                    return {"type": "invalid", "raw": text}
                return {
                    "type": "action",
                    "thought": thought,
                    "action": action_match.group(1).strip(),
                    "action_input": action_input,
                }
            return {"type": "invalid", "raw": text}

        if final_pos != -1:
            return {
                "type": "final_answer",
                "thought": thought,
                "final_answer": text[final_pos + len("Final Answer:"):].strip(),
            }

        return {"type": "invalid", "raw": text}

    def run(self, user_query: str) -> AgentState:
        state = AgentState(user_query=user_query)

        while not state.is_done and not state.is_max_iterations_reached():
            state.iteration += 1
            print(f"\n{'='*15} ITERATION {state.iteration} {'='*15}")

            scratchpad_text = state.render_scratchpad()
            user_content = f"Câu hỏi: {user_query}"
            if scratchpad_text:
                user_content += f"\n\n{scratchpad_text}"

            response = self.llm.chat(
                [{"role": "user", "content": user_content}],
                system_prompt=self.system_prompt,
                stop_sequences=["Observation:"],
            )

            print("--- RAW RESPONSE (nguyên văn từ LLM) ---")
            print(repr(response.text))   # dùng repr() để thấy rõ cả ký tự \n, khoảng trắng thừa
            print("--- END RAW ---")

            parsed = self.parse_llm_output(response.text)
            print("--- PARSED ---", parsed)

            # ... phần xử lý parsed["type"] giữ nguyên như cũ
            parsed = self.parse_llm_output(response.text)

            # 4. Xử lý theo loại kết quả parse được
            if parsed["type"] == "final_answer":
                if parsed["thought"]:
                    state.add_thought(parsed["thought"])
                state.final_answer = parsed["final_answer"]
                state.is_done = True

            elif parsed["type"] == "action":
                if parsed["thought"]:
                    state.add_thought(parsed["thought"])
                state.add_action(parsed["action"], parsed["action_input"])

                tool = self.tools.get(parsed["action"])
                if tool is None:
                    available = ", ".join(self.tools.keys())
                    observation = (
                        f"Lỗi: tool '{parsed['action']}' không tồn tại. "
                        f"Các tool khả dụng: {available}."
                    )
                else:
                    observation = tool.safe_run(**parsed["action_input"])

                state.add_observation(observation)

            else:  # "invalid"
                state.add_observation(
                    "Định dạng phản hồi không hợp lệ. Vui lòng tuân theo đúng format: "
                    "'Thought: ...' rồi 'Action: ...' + 'Action Input: {...}', "
                    "hoặc 'Thought: ...' rồi 'Final Answer: ...'."
                )

        if not state.is_done:
            state.final_answer = (
                "Xin lỗi, tôi chưa thể tìm ra câu trả lời đầy đủ trong giới hạn số bước xử lý."
            )

        return state