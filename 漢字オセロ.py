import tkinter as tk
import json
import os
import random

ROWS = 8
COLUMNS = 8
BASE_FONT_SIZE = 40  # 8x8に合わせて少し小さく -> 大きく変更
CONTROL_FONT_SIZE = 20
SAVE_FILE = "kanji_othello_state.json"
KANJI_FILE = "kanji.txt"
PLAYER_FILE = "players.txt"

# デフォルト設定
DEFAULT_PLAYERS = ["たっしー", "あきら", "おかゆん"]
PLAYER_COLORS_LIST = ["#FF6347", "#1E90FF", "#32CD32"] # 赤, 青, 緑

def load_players():
    names = []
    if os.path.exists(PLAYER_FILE):
        try:
            with open(PLAYER_FILE, "r", encoding="utf-8") as f:
                names = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"プレイヤー読み込みエラー: {e}")
            
    # 足りない場合はデフォルトまたは連番で埋める
    for i in range(len(names), 3):
        if i < len(DEFAULT_PLAYERS):
            names.append(DEFAULT_PLAYERS[i])
        else:
            names.append(f"プレイヤー{i+1}")
            
    # 最大3人まで
    names = names[:3]
            
    # 辞書作成
    p_colors = {}
    for i, name in enumerate(names):
        p_colors[name] = PLAYER_COLORS_LIST[i]
        
    return names, p_colors

# プレイヤー読み込み
player_names_list, player_colors = load_players()

def load_kanji():
    if os.path.exists(KANJI_FILE):
        with open(KANJI_FILE, "r", encoding="utf-8") as f:
            kanjis = [line.strip() for line in f if line.strip()]
        # 足りない場合は補充
        while len(kanjis) < ROWS * COLUMNS:
            kanjis.append(f"漢字{len(kanjis)+1}")
        return kanjis[:ROWS * COLUMNS]
    return [f"漢字{i+1}" for i in range(ROWS * COLUMNS)]

class OthelloApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("漢字オセロ（3人対戦）")

        # 起動時に最大化
        try:
            self.state('zoomed')  # Windows用
        except:
            self.attributes('-zoomed', True)  # macOS/Linux用

        self.selected_player = None
        self.click_action = None # None, 'show_kanji', 'claim'

        self.cell_widgets = []
        self.cell_owners = [[None] * COLUMNS for _ in range(ROWS)]
        
        # 初期状態の設定：角(0,0),(0,7),(7,0),(7,7)以外は最初からオープン
        self.cell_revealed = [[True] * COLUMNS for _ in range(ROWS)]
        self.cell_revealed[0][0] = False
        self.cell_revealed[0][COLUMNS-1] = False
        self.cell_revealed[ROWS-1][0] = False
        self.cell_revealed[ROWS-1][COLUMNS-1] = False

        # 初期配置の設定（センター4マス）
        # 28(3,3), 37(4,4) -> Player 1 (names[0])
        # 29(3,4) -> Player 2 (names[1])
        # 36(4,3) -> Player 3 (names[2])
        if len(player_names_list) >= 3:
            p1 = player_names_list[0]
            p2 = player_names_list[1]
            p3 = player_names_list[2]
            
            self.cell_owners[3][3] = p1
            self.cell_owners[4][4] = p1
            self.cell_owners[3][4] = p2
            self.cell_owners[4][3] = p3
        
        
        self.player_buttons = {}
        self.player_counts = {name: 0 for name in player_colors}
        self.player_count_labels = {}

        self.kanji_list = load_kanji()

        self.load_board_state()
        self.build_board_window()
        self.create_control_window()
        self.update_counts()

    def build_board_window(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        board = tk.Frame(self)
        board.grid(row=0, column=0, sticky="nsew")
        board.grid_propagate(False)

        for c in range(COLUMNS):
            board.columnconfigure(c, weight=1)
        for r in range(ROWS):
            board.rowconfigure(r, weight=1)

        for r in range(ROWS):
            row_cells = []
            for c in range(COLUMNS):
                cell = tk.Label(board, text="", bg="#f8f8f8", fg="black",
                                font=("Arial", BASE_FONT_SIZE), relief=tk.GROOVE,
                                width=4, height=2)
                cell.grid(row=r, column=c, sticky="nsew")
                cell.bind("<Button-1>", lambda e, x=r, y=c: self.on_cell_click(x, y))
                cell.bind("<Button-3>", lambda e, x=r, y=c: self.clear_cell(x, y))
                row_cells.append(cell)
            self.cell_widgets.append(row_cells)
        
        # 初回描画更新
        for r in range(ROWS):
            for c in range(COLUMNS):
                self.update_cell_display(r, c)

    def create_control_window(self):
        self.control_window = tk.Toplevel(self)
        self.control_window.title("コントロール")
        self.control_window.geometry("400x300")

        # モード選択ボタン
        mode_frame = tk.Frame(self.control_window)
        mode_frame.pack(pady=10)
        
        self.mode_label = tk.Label(self.control_window, text="現在のモード: 未選択", font=("Arial", 16))
        self.mode_label.pack(pady=5)

        tk.Button(mode_frame, text="出題（漢字オープン）", command=self.set_mode_show_kanji, bg="#ddd", font=("Arial", 14)).pack(side=tk.LEFT, padx=5)

        # プレイヤー選択
        lbl = tk.Label(self.control_window, text="正解者を選択してマスを獲得:", font=("Arial", 14))
        lbl.pack(pady=(20, 5))

        btn_frame = tk.Frame(self.control_window)
        btn_frame.pack(pady=5)
        for name, color in player_colors.items():
            btn = tk.Button(btn_frame, text=name,
                            font=("Arial", 14),
                            bg=color, fg="white",
                            command=lambda n=name: self.set_selected_player(n))
            btn.pack(side=tk.LEFT, padx=5)
            self.player_buttons[name] = btn

        # スコア表示
        score_frame = tk.Frame(self.control_window)
        score_frame.pack(pady=20)
        for name in player_colors:
            lbl = tk.Label(score_frame, text=f"{name}: 0",
                           font=("Arial", 14),
                           bg=player_colors[name], fg="white", width=12)
            lbl.pack(pady=2)
            self.player_count_labels[name] = lbl

    def set_mode_show_kanji(self):
        self.click_action = 'show_kanji'
        self.selected_player = None
        self.mode_label.config(text="モード: 出題（マスをクリックして漢字を表示）")
        for btn in self.player_buttons.values():
            btn.config(relief=tk.RAISED)

    def set_selected_player(self, name):
        self.selected_player = name
        self.click_action = 'claim'
        self.mode_label.config(text=f"モード: {name} のターン（正解マスをクリック）")
        for pname, btn in self.player_buttons.items():
            btn.config(relief=tk.SUNKEN if pname == name else tk.RAISED)

    def on_cell_click(self, x, y):
        # 範囲外チェック
        if not (0 <= x < ROWS and 0 <= y < COLUMNS):
            return

        if self.click_action == 'show_kanji':
            self.cell_revealed[x][y] = True
            self.update_cell_display(x, y)
            self.save_board_state()

        elif self.click_action == 'claim' and self.selected_player:
            # 既に石がある場合は何もしない
            if self.cell_owners[x][y] is not None:
                return 
            
            # 石を置く
            self.cell_owners[x][y] = self.selected_player
            self.cell_revealed[x][y] = True 
            self.update_cell_display(x, y)
            
            # オセロの裏返し処理
            self.flip_enclosed_cells(x, y)
            
            self.update_counts()
            self.save_board_state()

    def update_cell_display(self, x, y):
        cell = self.cell_widgets[x][y]
        owner = self.cell_owners[x][y]
        revealed = self.cell_revealed[x][y]
        
        kanji = self.kanji_list[x * COLUMNS + y]
        num = x * COLUMNS + y + 1
        
        display_text = ""
        
        if owner:
            # 獲得済み：番号、漢字、プレイヤー名
            display_text = f"{num}\n{kanji}\n{owner}"
            bg = player_colors[owner]
            fg = "white"
        elif revealed:
            # オープン済み：番号、漢字
            display_text = f"{num}\n{kanji}"
            bg = "#ffffff"
            fg = "black"
        else:
            # 未オープン（角など）：番号のみ
            display_text = str(num)
            bg = "#f8f8f8"
            fg = "black"
            
        cell.config(text=display_text, bg=bg, fg=fg)
        
        # フォントサイズ調整
        # 3行になる場合もあるのでさらに小さく調整、または可変に
        line_count = display_text.count('\n') + 1
        if line_count >= 3:
             cell.config(font=("Arial", BASE_FONT_SIZE - 22)) # 18pt (3行)
        elif line_count == 2:
             cell.config(font=("Arial", BASE_FONT_SIZE - 12)) # 28pt (2行)
        else:
             cell.config(font=("Arial", BASE_FONT_SIZE))      # 40pt (1行)

    def flip_enclosed_cells(self, x, y):
        # 8方向
        directions = [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]
        
        for dx, dy in directions:
            flipped = []
            cx, cy = x + dx, y + dy
            
            while 0 <= cx < ROWS and 0 <= cy < COLUMNS:
                owner = self.cell_owners[cx][cy]
                
                if owner is None:
                    # 空白マスに突き当たったら、挟めていないので終了
                    break
                
                if owner == self.selected_player:
                    # 自分の色に突き当たったら、溜めていたflippedを裏返す
                    for fx, fy in flipped:
                        self.cell_owners[fx][fy] = self.selected_player
                        self.update_cell_display(fx, fy)
                    break 
                else:
                    # 相手の色ならフリップ候補に追加して次へ
                    flipped.append((cx, cy))
                
                cx += dx
                cy += dy

    def clear_cell(self, x, y):
        # 右クリックでリセット（デバッグや誤操作用）
        self.cell_owners[x][y] = None
        self.cell_revealed[x][y] = False
        self.update_cell_display(x, y)
        self.update_counts()
        self.save_board_state()

    def update_counts(self):
        self.player_counts = {name: 0 for name in player_colors}
        for r in range(ROWS):
            for c in range(COLUMNS):
                owner = self.cell_owners[r][c]
                if owner in self.player_counts:
                    self.player_counts[owner] += 1
        
        for name in player_colors:
            self.player_count_labels[name].config(
                text=f"{name}: {self.player_counts[name]}")

    def save_board_state(self):
        state = {
            "owners": self.cell_owners,
            "revealed": self.cell_revealed
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)

    def load_board_state(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    # 古い形式(リストのみ)か新しい形式(辞書)かチェック
                    if isinstance(state, list):
                         self.cell_owners = state
                         # revealedは全部Falseか、ownerがいればTrueにするなどの互換処理
                         for r in range(ROWS):
                             for c in range(COLUMNS):
                                 if self.cell_owners[r][c]:
                                     self.cell_revealed[r][c] = True
                    elif isinstance(state, dict):
                        self.cell_owners = state.get("owners", [[None]*COLUMNS for _ in range(ROWS)])
                        self.cell_revealed = state.get("revealed", [[False]*COLUMNS for _ in range(ROWS)])
                        
                    # サイズが変わっている場合のガード
                    if len(self.cell_owners) != ROWS or len(self.cell_owners[0]) != COLUMNS:
                         print("サイズ不一致のため初期化します")
                         self.cell_owners = [[None] * COLUMNS for _ in range(ROWS)]
                         self.cell_revealed = [[False] * COLUMNS for _ in range(ROWS)]
                         
            except Exception as e:
                print("読み込み失敗:", e)

if __name__ == "__main__":
    app = OthelloApp()
    app.mainloop()
