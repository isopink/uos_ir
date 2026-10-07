"""숫자 야구 게임.

컴퓨터가 서로 다른 숫자 3자리를 정하면, 플레이어가 맞힌다.
- 스트라이크: 숫자와 자리가 모두 맞음
- 볼: 숫자는 있지만 자리가 다름
- 아웃: 하나도 맞지 않음
"""
import random

DIGITS = 3


def make_answer():
    return random.sample("0123456789", DIGITS)


def read_guess():
    while True:
        guess = input(f"서로 다른 숫자 {DIGITS}자리를 입력하세요: ").strip()
        if len(guess) == DIGITS and guess.isdigit() and len(set(guess)) == DIGITS:
            return list(guess)
        print("잘못된 입력입니다. 다시 입력해 주세요.")


def judge(answer, guess):
    strike = sum(a == g for a, g in zip(answer, guess))
    ball = len(set(answer) & set(guess)) - strike
    return strike, ball


def play():
    answer = make_answer()
    tries = 0
    while True:
        guess = read_guess()
        tries += 1
        strike, ball = judge(answer, guess)
        if strike == DIGITS:
            print(f"정답! {tries}번 만에 맞혔습니다.")
            return
        if strike == ball == 0:
            print("아웃")
        else:
            print(f"{strike} 스트라이크 {ball} 볼")


def main():
    print("=== 숫자 야구 게임 ===")
    while True:
        play()
        if input("다시 하시겠습니까? (y/n): ").strip().lower() != "y":
            print("게임을 종료합니다.")
            break


if __name__ == "__main__":
    main()
