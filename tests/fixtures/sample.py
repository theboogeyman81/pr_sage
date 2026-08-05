def top_function(x: int) -> int:
    return x + 1


class MyClass:
    def method_one(self) -> None:
        pass

    async def method_two(self) -> str:
        return "hello"

    @staticmethod
    def static_method() -> None:
        pass


@some_decorator
def decorated_function() -> None:
    pass
