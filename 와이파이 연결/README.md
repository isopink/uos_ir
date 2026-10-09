# 실습실에서 Jetson SSH + 인터넷(Claude Code) 동시에 쓰기

## 문제

- Jetson에 SSH 접속하려면 노트북을 실습실 Wi-Fi(`rcv-robot` / `rcv-robot-5G`)에 연결해야 한다
- 이 Wi-Fi에는 인터넷이 없다 → **Claude Code(인터넷 필요)를 쓸 수 없다**
- 인터넷 되는 Wi-Fi로 바꾸면 → Jetson에 접속이 안 된다

## 핵심

노트북 Wi-Fi 장치는 **한 번에 Wi-Fi 하나에만** 연결된다.
→ **네트워크 통로를 물리적으로 2개** 만들어야 한다.

```
노트북 ─┬─ 통로 1 → rcv-robot (Jetson SSH)
        └─ 통로 2 → 인터넷 (Claude Code)
```

## 방법 1. 유선 랜

```
노트북 ─┬─ Wi-Fi 장치    → rcv-robot (Jetson SSH)
        └─ 랜 포트 (선)  → 학교 인터넷 (Claude Code)
```

- 유선 랜은 Wi-Fi와 **별개의 부품(통로)** 이다. Wi-Fi로 들어가는 것이 아니므로 동시에 쓸 수 있다
- 필요 조건
  - [ ] 실습실에 **인터넷 되는 랜 포트**가 있어야 함 (조교님께 확인, 학교 유선망은 기기 등록이 필요할 수 있음)
  - [ ] 노트북에 랜 포트가 있어야 함 → 없으면 **USB-랜 어댑터** (1만 원대)

## 방법 2. USB Wi-Fi 동글 ⭐ (랜 포트가 없을 때)

```
노트북 ─┬─ 내장 Wi-Fi       → 인터넷 되는 Wi-Fi (Claude Code)
        └─ USB Wi-Fi 동글   → rcv-robot (Jetson SSH)
```

- USB에 꽂는 작은 Wi-Fi 장치 (1~2만 원대) → Wi-Fi 장치가 2개가 되어 Wi-Fi 2개에 동시 연결
- 실습실 랜 포트 유무와 상관없이 사용 가능
- `rcv-robot-5G`에 연결하려면 **5GHz 지원** 제품으로 구매

## Docker / 가상머신으로는 안 되는 이유

팀 내에서 나온 아이디어: "Docker로 윈도우와 맥을 동시에 띄워서, 한쪽은 rcv-robot, 한쪽은 인터넷 Wi-Fi에 연결"

- **Docker는 운영체제(윈도우/맥)를 하나 더 띄우는 도구가 아니다.** 프로그램과 그 실행 환경을 상자(컨테이너)에 담아 실행하는 도구이며, macOS는 Docker로 실행할 수 없다
- 운영체제를 하나 더 띄우는 것은 가상머신(VM)이지만, 이것도 안 된다
  - 가상머신은 노트북의 **같은 Wi-Fi 장치를 빌려 쓴다** → 따로 다른 Wi-Fi에 연결할 수 없음
  - Docker 컨테이너도 마찬가지로 노트북의 네트워크를 빌려 씀

```
노트북 Wi-Fi 장치 1개 ── 연결 가능한 Wi-Fi도 1개
   ├─ 윈도우
   └─ 가상머신 / Docker → 같은 Wi-Fi만 씀 (따로 연결 ✗)
```

> Docker는 **환경 문제**(예: Ubuntu 20.04 Jetson에서 22.04용 ROS 2 Humble 실행)를 푸는 도구이고, **네트워크 통로 문제**는 풀지 못한다.

## 연결 후 확인 (Windows PowerShell)

두 통로를 연결한 뒤:

```powershell
# 1. 네트워크 2개가 모두 연결되어 있는지
Get-NetConnectionProfile

# 2. 인터넷 확인
Test-NetConnection google.com -Port 443

# 3. Jetson SSH 포트 확인 (<JETSON_IP>는 조교님 IP List 참고)
Test-NetConnection <JETSON_IP> -Port 22
```

보통 Windows가 자동으로 "Jetson 주소는 rcv-robot 쪽, 나머지 인터넷은 다른 통로"로 보내준다.

### 인터넷이 안 될 때

rcv-robot 쪽이 기본 경로로 잡혀서 인터넷 요청이 그쪽으로 가는 경우다.
**관리자 권한 PowerShell**에서 rcv-robot 쪽 통로의 우선순위를 낮춘다 (숫자가 클수록 우선순위 낮음):

```powershell
# 통로 이름과 현재 우선순위 확인
Get-NetIPInterface -AddressFamily IPv4 | Sort-Object InterfaceMetric

# rcv-robot에 연결된 통로 이름(예: "Wi-Fi 2")의 우선순위 낮추기
Set-NetIPInterface -InterfaceAlias "<rcv-robot 통로 이름>" -InterfaceMetric 100
```

## 연결되면 할 수 있는 것

- 실습실에서도 노트북 Claude Code로 대화하며 작업
- Claude Code가 노트북에서 `ssh`로 Jetson 명령을 대신 실행 (예: `printenv ROS_DISTRO` 확인)
- Jetson 안전 규칙(`apt upgrade` 금지 등)은 그대로 지킴

## 확인 필요

- [ ] 실습실에 인터넷 되는 랜 포트가 있는지 (조교님)
- [ ] 노트북 랜 포트 유무
- [ ] Jetson IP (조교님 IP List)
