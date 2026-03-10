from learnbox.llm import ask


def main():
    print("LearnBox — type a question, or 'quit' to exit.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "/bye"):
            print("Goodbye.")
            break

        print("LearnBox: (thinking...)", flush=True)
        try:
            response = ask(user_input, timeout=120.0)
            print(f"LearnBox: {response}")
        except RuntimeError as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
