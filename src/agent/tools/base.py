import inspect
from abc import ABC, abstractmethod
from typing import get_type_hints


PYTHON_TO_JSON_TYPE = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


class BaseTool(ABC):
    name: str
    description: str

    # Optional: tool con có thể override để mô tả rõ từng tham số,
    # giúp LLM hiểu đúng ý nghĩa tham số khi quyết định gọi tool (không chỉ dựa vào tên biến).
    # Ví dụ: {"query": "Câu hỏi cần tìm kiếm trong tài liệu", "top_k": "Số lượng kết quả trả về"}
    param_descriptions: dict[str, str] = {}

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Thực thi tool. Luôn trả về string để đưa vào Observation của ReAct loop."""
        ...

    @classmethod
    def get_schema(cls) -> dict:
        """
        Tự động trích JSON Schema từ signature của run(), dùng cho function calling.
        """
        sig = inspect.signature(cls.run)
        hints = get_type_hints(cls.run)

        properties = {}
        required = []

        for name, param in sig.parameters.items():
            if name == "self":
                continue

            python_type = hints.get(name, str)
            json_type = PYTHON_TO_JSON_TYPE.get(python_type, "string")

            prop = {"type": json_type}
            if name in cls.param_descriptions:
                prop["description"] = cls.param_descriptions[name]
            properties[name] = prop

            if param.default is inspect.Parameter.empty:
                required.append(name)

        return {
            "name": cls.name,
            "description": cls.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    @property
    def schema(self) -> dict:
        return self.get_schema()

    def safe_run(self, **kwargs) -> str:
        """
        Wrapper quanh run() — bắt mọi lỗi phát sinh khi tool chạy sai tham số hoặc lỗi nội bộ,
        trả về string mô tả lỗi thay vì crash. Quan trọng vì ReAct loop (Sprint 3 sau) sẽ gọi
        tool dựa trên tham số do LLM tự sinh ra — LLM có thể truyền sai kiểu/tên tham số,
        và Agent cần tiếp tục vòng lặp (đưa lỗi vào Observation) thay vì toàn bộ chương trình dừng.
        """
        try:
            return self.run(**kwargs)
        except TypeError as e:
            return f"Lỗi: tham số truyền vào tool '{self.name}' không hợp lệ ({e})"
        except Exception as e:
            return f"Lỗi khi chạy tool '{self.name}': {e}"