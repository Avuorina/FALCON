from core.brain import ask_claude

def main():
    print("FALCON起動しました。「終了」と入力すると終わります。")
    
    while True:
        user_input = input("隼: ")
        
        if user_input == "終了":
            print("FALCON: またな、隼。")
            break
        
        reply = ask_claude(user_input)
        print(f"FALCON: {reply}")


if __name__ == "__main__":
    main()