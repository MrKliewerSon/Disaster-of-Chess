import pygame
import sys
import math
import random
from enum import Enum
from dataclasses import dataclass

# Initialize pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
BOARD_SIZE = 8
SQUARE_SIZE = 80
BOARD_OFFSET_X = 50
BOARD_OFFSET_Y = 50
UI_HEIGHT = 100

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
HIGHLIGHT = (124, 179, 66)
SELECTED = (255, 255, 0)
RED = (255, 0, 0)

# Biome colors (for rows 3-6)
ICE_BIOME_LIGHT = (200, 230, 255)
ICE_BIOME_DARK = (150, 200, 255)
PLAINS_BIOME_LIGHT = (200, 220, 150)
PLAINS_BIOME_DARK = (180, 200, 120)
STORMY_BIOME_LIGHT = (180, 180, 200)
STORMY_BIOME_DARK = (150, 150, 180)
NORMAL_BIOME_LIGHT = (240, 217, 181)
NORMAL_BIOME_DARK = (181, 136, 99)

class PieceType(Enum):
    PAWN = 1
    ROOK = 2
    KNIGHT = 3
    BISHOP = 4
    QUEEN = 5
    KING = 6

class PieceColor(Enum):
    WHITE = 1
    BLACK = 2

@dataclass
class Piece:
    piece_type: PieceType
    color: PieceColor
    row: int
    col: int
    has_moved: bool = False  # Track if piece has moved (for castling and pawn promotion)

class ChessBoard:
    def __init__(self):
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.initialize_pieces()
        self.selected_piece = None
        self.valid_moves = []
        self.current_player = PieceColor.WHITE
        self.move_history = []
        self.en_passant_target = None  # For en passant capture
        self.game_state = "playing"  # playing, check, checkmate, stalemate
        self.game_message = ""
        self.blackout_active = False
        self.blackout_turns_left = 0
        self.blackout_quadrant = None
        self.frozen_pieces = {}  # {(row, col): turns_left}
        self.biome_message = ""
        
    def initialize_pieces(self):
        # Black pieces (top)
        self.place_piece(0, 0, PieceType.ROOK, PieceColor.BLACK)
        self.place_piece(0, 1, PieceType.KNIGHT, PieceColor.BLACK)
        self.place_piece(0, 2, PieceType.BISHOP, PieceColor.BLACK)
        self.place_piece(0, 3, PieceType.QUEEN, PieceColor.BLACK)
        self.place_piece(0, 4, PieceType.KING, PieceColor.BLACK)
        self.place_piece(0, 5, PieceType.BISHOP, PieceColor.BLACK)
        self.place_piece(0, 6, PieceType.KNIGHT, PieceColor.BLACK)
        self.place_piece(0, 7, PieceType.ROOK, PieceColor.BLACK)
        
        for col in range(BOARD_SIZE):
            self.place_piece(1, col, PieceType.PAWN, PieceColor.BLACK)
        
        # White pieces (bottom)
        for col in range(BOARD_SIZE):
            self.place_piece(6, col, PieceType.PAWN, PieceColor.WHITE)
        
        self.place_piece(7, 0, PieceType.ROOK, PieceColor.WHITE)
        self.place_piece(7, 1, PieceType.KNIGHT, PieceColor.WHITE)
        self.place_piece(7, 2, PieceType.BISHOP, PieceColor.WHITE)
        self.place_piece(7, 3, PieceType.QUEEN, PieceColor.WHITE)
        self.place_piece(7, 4, PieceType.KING, PieceColor.WHITE)
        self.place_piece(7, 5, PieceType.BISHOP, PieceColor.WHITE)
        self.place_piece(7, 6, PieceType.KNIGHT, PieceColor.WHITE)
        self.place_piece(7, 7, PieceType.ROOK, PieceColor.WHITE)
    
    def place_piece(self, row, col, piece_type, color):
        piece = Piece(piece_type, color, row, col)
        self.board[row][col] = piece
    
    def get_piece(self, row, col):
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return self.board[row][col]
        return None
    
    def get_valid_moves(self, row, col):
        piece = self.get_piece(row, col)
        if piece is None:
            return []
        
        # Frozen pieces cannot move
        if self.is_piece_frozen(row, col):
            return []
        
        moves = []
        
        if piece.piece_type == PieceType.PAWN:
            direction = 1 if piece.color == PieceColor.BLACK else -1
            # Move forward
            new_row = row + direction
            if 0 <= new_row < BOARD_SIZE and self.board[new_row][col] is None:
                moves.append((new_row, col))
                # First move can be two squares
                start_row = 1 if piece.color == PieceColor.BLACK else 6
                if row == start_row:
                    new_row = row + 2 * direction
                    if self.board[new_row][col] is None:
                        moves.append((new_row, col))
            
            # Capture diagonally
            for new_col in [col - 1, col + 1]:
                new_row = row + direction
                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    target = self.board[new_row][new_col]
                    if target and target.color != piece.color:
                        moves.append((new_row, new_col))
            
            # En passant
            if self.en_passant_target:
                en_row, en_col = self.en_passant_target
                if row == en_row and abs(col - en_col) == 1:
                    moves.append((en_row - direction, en_col))
        
        elif piece.piece_type == PieceType.ROOK:
            moves = self._get_sliding_moves(row, col, [(0, 1), (0, -1), (1, 0), (-1, 0)])
        
        elif piece.piece_type == PieceType.BISHOP:
            moves = self._get_sliding_moves(row, col, [(1, 1), (1, -1), (-1, 1), (-1, -1)])
        
        elif piece.piece_type == PieceType.QUEEN:
            moves = self._get_sliding_moves(row, col, [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)])
        
        elif piece.piece_type == PieceType.KNIGHT:
            knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
            for dr, dc in knight_moves:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                    target = self.board[new_row][new_col]
                    if target is None or target.color != piece.color:
                        moves.append((new_row, new_col))
        
        elif piece.piece_type == PieceType.KING:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    new_row, new_col = row + dr, col + dc
                    if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                        target = self.board[new_row][new_col]
                        if target is None or target.color != piece.color:
                            moves.append((new_row, new_col))
            
            # Castling
            if not piece.has_moved and not self.is_king_in_check(piece.color):
                # King-side castling
                rook = self.board[row][7]
                if rook and rook.piece_type == PieceType.ROOK and not rook.has_moved:
                    if self.board[row][5] is None and self.board[row][6] is None:
                        if not self.is_square_attacked(row, 5, PieceColor.BLACK if piece.color == PieceColor.WHITE else PieceColor.WHITE):
                            moves.append((row, 6))
                
                # Queen-side castling
                rook = self.board[row][0]
                if rook and rook.piece_type == PieceType.ROOK and not rook.has_moved:
                    if self.board[row][1] is None and self.board[row][2] is None and self.board[row][3] is None:
                        if not self.is_square_attacked(row, 3, PieceColor.BLACK if piece.color == PieceColor.WHITE else PieceColor.WHITE):
                            moves.append((row, 2))
        
        return moves
    
    def _get_sliding_moves(self, row, col, directions):
        piece = self.get_piece(row, col)
        moves = []
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            while 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                target = self.board[new_row][new_col]
                if target is None:
                    moves.append((new_row, new_col))
                elif target.color != piece.color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break
                new_row += dr
                new_col += dc
        
        return moves
    
    def select_piece(self, row, col):
        piece = self.get_piece(row, col)
        if piece and piece.color == self.current_player:
            self.selected_piece = (row, col)
            self.valid_moves = self.get_valid_moves(row, col)
            return True
        return False
    
    def get_biome(self, row, col):
        """Return biome type for a square. Biomes only in rows 2-5."""
        # Only apply biomes to rows 2, 3, 4, 5
        if row < 2 or row > 5:
            return "normal"
        
        # Rows 2-3 are top (ice/stormy), rows 4-5 are bottom (plains/normal)
        is_top = row < 4
        # Cols 0-3 are left, cols 4-7 are right
        is_left = col < 4
        
        if is_top and is_left:
            return "ice"
        elif is_top and not is_left:
            return "stormy"
        elif not is_top and is_left:
            return "plains"
        else:
            return "normal"
    
    def freeze_piece(self, row, col, turns=1):
        """Freeze a piece for specified turns"""
        if self.board[row][col] is not None:
            self.frozen_pieces[(row, col)] = turns
    
    def decrement_freeze_timers(self):
        """Decrement freeze timers and remove expired freezes"""
        expired = []
        for pos, turns in self.frozen_pieces.items():
            self.frozen_pieces[pos] -= 1
            if self.frozen_pieces[pos] <= 0:
                expired.append(pos)
        for pos in expired:
            del self.frozen_pieces[pos]
    
    def is_piece_frozen(self, row, col):
        """Check if a piece is frozen"""
        return (row, col) in self.frozen_pieces

    def get_blackout_bounds(self):
        """Return the row/col bounds for the current blackout quadrant."""
        if self.blackout_quadrant == 0:
            return (0, 3, 0, 3)
        if self.blackout_quadrant == 1:
            return (0, 3, 4, 7)
        if self.blackout_quadrant == 2:
            return (4, 7, 0, 3)
        if self.blackout_quadrant == 3:
            return (4, 7, 4, 7)
        return None

    def is_in_blackout(self, row, col):
        """Check if a square is covered by blackout."""
        bounds = self.get_blackout_bounds()
        if bounds is None:
            return False
        min_row, max_row, min_col, max_col = bounds
        return min_row <= row <= max_row and min_col <= col <= max_col

    def activate_blackout(self):
        """Start a blackout on a random quadrant for 2 turns."""
        self.blackout_quadrant = random.randint(0, 3)
        self.blackout_active = True
        self.blackout_turns_left = 2

    def decrement_blackout_turn(self):
        """Count down blackout duration after each completed move."""
        if self.blackout_active:
            self.blackout_turns_left -= 1
            if self.blackout_turns_left <= 0:
                self.blackout_active = False
                self.blackout_quadrant = None
                self.blackout_turns_left = 0

    def apply_lightning_strike(self):
        """Strike a random square in stormy biome (rows 2-3, cols 4-7). 1/4 chance to trigger blackout."""
        strike_row = random.choice([2, 3])
        strike_col = random.randint(4, 7)
        struck_piece = self.board[strike_row][strike_col]
        self.board[strike_row][strike_col] = None

        if self.selected_piece == (strike_row, strike_col):
            self.selected_piece = None
            self.valid_moves = []

        if struck_piece:
            piece_name = struck_piece.piece_type.name.lower()
            self.game_message = f"Lightning: removed {piece_name} on row {strike_row + 1}."
        else:
            self.game_message = f"Lightning: empty square on row {strike_row + 1}."
        
        # 1/4 chance to trigger blackout
        if random.random() < 0.25:
            self.activate_blackout()
            self.game_message += " BLACKOUT TRIGGERED!"
        
        return (strike_row, strike_col)
    
    def apply_freeze_disaster(self):
        """Freeze random pieces in ice biome (rows 2-3, cols 0-3) for 1 turn"""
        ice_pieces = []
        for row in [2, 3]:
            for col in range(4):
                piece = self.board[row][col]
                if piece:
                    ice_pieces.append((row, col))
        
        if ice_pieces:
            freeze_targets = random.sample(ice_pieces, min(2, len(ice_pieces)))
            for pos in freeze_targets:
                self.freeze_piece(pos[0], pos[1], turns=1)
            self.biome_message = f"Ice biome: {len(freeze_targets)} pieces frozen!"
        else:
            self.biome_message = "Ice biome: no pieces to freeze!"
    
    def apply_wind_disaster(self):
        """Push pieces in plains biome (rows 4-5, cols 0-3) left by one square"""
        affected_rows = [4, 5]
        pieces_to_move = []
        
        # Collect pieces in affected rows of plains biome
        for row in affected_rows:
            for col in range(4):
                piece = self.board[row][col]
                if piece:
                    pieces_to_move.append((row, col, piece))
        
        # Move pieces left, starting from leftmost to avoid collisions
        for row, col, piece in sorted(pieces_to_move, key=lambda x: x[1]):
            if col > 0 and self.board[row][col - 1] is None:
                self.board[row][col] = None
                self.board[row][col - 1] = piece
                piece.col = col - 1
    
    def find_king(self, color):
        """Find king position for given color"""
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece and piece.piece_type == PieceType.KING and piece.color == color:
                    return (row, col)
        return None
    
    def is_square_attacked(self, row, col, by_color):
        """Check if a square is attacked by pieces of given color"""
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if piece and piece.color == by_color:
                    # Check if this piece can attack the square
                    if self._can_piece_attack(r, c, row, col):
                        return True
        return False
    
    def _can_piece_attack(self, from_row, from_col, to_row, to_col):
        """Check if piece at (from_row, from_col) can attack (to_row, to_col)"""
        piece = self.board[from_row][from_col]
        if not piece:
            return False
        
        if piece.piece_type == PieceType.PAWN:
            direction = 1 if piece.color == PieceColor.BLACK else -1
            if to_row == from_row + direction and abs(to_col - from_col) == 1:
                return True
        
        elif piece.piece_type == PieceType.KNIGHT:
            knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
            if (to_row - from_row, to_col - from_col) in knight_moves:
                return True
        
        elif piece.piece_type == PieceType.KING:
            if abs(to_row - from_row) <= 1 and abs(to_col - from_col) <= 1:
                return True
        
        elif piece.piece_type in [PieceType.ROOK, PieceType.BISHOP, PieceType.QUEEN]:
            directions = []
            if piece.piece_type in [PieceType.ROOK, PieceType.QUEEN]:
                directions += [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if piece.piece_type in [PieceType.BISHOP, PieceType.QUEEN]:
                directions += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
            
            for dr, dc in directions:
                r, c = from_row + dr, from_col + dc
                while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                    if r == to_row and c == to_col:
                        return True
                    if self.board[r][c] is not None:
                        break
                    r += dr
                    c += dc
        
        return False
    
    def is_king_in_check(self, color):
        """Check if king of given color is in check"""
        king_pos = self.find_king(color)
        if not king_pos:
            return False
        enemy_color = PieceColor.BLACK if color == PieceColor.WHITE else PieceColor.WHITE
        return self.is_square_attacked(king_pos[0], king_pos[1], enemy_color)
    
    def is_legal_move(self, from_row, from_col, to_row, to_col):
        """Check if move leaves king in check"""
        # Simulate the move
        original_piece = self.board[to_row][to_col]
        moving_piece = self.board[from_row][from_col]
        
        self.board[from_row][from_col] = None
        self.board[to_row][to_col] = moving_piece
        
        # Check if king is in check
        is_legal = not self.is_king_in_check(moving_piece.color)
        
        # Undo the move
        self.board[from_row][from_col] = moving_piece
        self.board[to_row][to_col] = original_piece
        
        return is_legal
    
    def has_legal_moves(self, color):
        """Check if a player has any legal moves"""
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece and piece.color == color:
                    moves = self.get_valid_moves(row, col)
                    for move_row, move_col in moves:
                        if self.is_legal_move(row, col, move_row, move_col):
                            return True
        return False
    
    def update_game_state(self):
        """Update game state after a move"""
        if self.is_king_in_check(self.current_player):
            if not self.has_legal_moves(self.current_player):
                self.game_state = "checkmate"
                self.game_message = f"Checkmate! {'Black' if self.current_player == PieceColor.BLACK else 'White'} wins!"
            else:
                self.game_state = "check"
                self.game_message = f"Check! {self.current_player.name} king is in check!"
        elif not self.has_legal_moves(self.current_player):
            self.game_state = "stalemate"
            self.game_message = "Stalemate! The game is a draw!"
        else:
            self.game_state = "playing"
            self.game_message = ""
    
    def select_piece(self, row, col):
        piece = self.get_piece(row, col)
        if piece and piece.color == self.current_player:
            self.selected_piece = (row, col)
            self.valid_moves = self.get_valid_moves(row, col)
            return True
        return False
    
    def move_piece(self, to_row, to_col):
        if self.selected_piece is None or self.game_state == "checkmate" or self.game_state == "stalemate":
            return False
        
        from_row, from_col = self.selected_piece
        if (to_row, to_col) not in self.valid_moves:
            return False
        
        # Check if move is legal (doesn't leave king in check)
        if not self.is_legal_move(from_row, from_col, to_row, to_col):
            return False
        
        piece = self.board[from_row][from_col]
        captured_piece = self.board[to_row][to_col]
        
        # Handle en passant
        if piece.piece_type == PieceType.PAWN and to_col != from_col and captured_piece is None:
            # This is en passant
            pawn_row = from_row
            self.board[pawn_row][to_col] = None
        
        # Move piece
        self.board[from_row][from_col] = None
        self.board[to_row][to_col] = piece
        piece.row = to_row
        piece.col = to_col
        piece.has_moved = True
        
        # Handle pawn promotion
        if piece.piece_type == PieceType.PAWN:
            if (piece.color == PieceColor.WHITE and to_row == 0) or (piece.color == PieceColor.BLACK and to_row == 7):
                # Promote to queen (you can change this to allow choice later)
                piece.piece_type = PieceType.QUEEN
        
        # Handle castling
        if piece.piece_type == PieceType.KING and abs(to_col - from_col) == 2:
            # Castling move
            if to_col > from_col:  # King-side castling
                rook = self.board[to_row][7]
                self.board[to_row][7] = None
                self.board[to_row][5] = rook
                rook.col = 5
            else:  # Queen-side castling
                rook = self.board[to_row][0]
                self.board[to_row][0] = None
                self.board[to_row][3] = rook
                rook.col = 3
            rook.has_moved = True
        
        # Update en passant target
        if piece.piece_type == PieceType.PAWN and abs(to_row - from_row) == 2:
            self.en_passant_target = (from_row + (to_row - from_row) // 2, from_col)
        else:
            self.en_passant_target = None
        
        # Switch player
        self.current_player = PieceColor.BLACK if self.current_player == PieceColor.WHITE else PieceColor.WHITE
        
        # Update game state
        self.update_game_state()

        # Count down blackout after a completed move
        self.decrement_blackout_turn()
        
        # Decrement freeze timers
        self.decrement_freeze_timers()
        
        # Clear selection
        self.selected_piece = None
        self.valid_moves = []
        
        return True


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Chess with Natural Disasters")
        self.clock = pygame.time.Clock()
        self.board = ChessBoard()
        
        self.font = pygame.font.Font(None, 36)
        # Use Segoe UI Symbol which supports Unicode chess symbols
        self.piece_font = pygame.font.SysFont("Segoe UI Symbol", 60)
        
        self.small_font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 48)
        self.wind_triggered = False
        self.wind_timer = 0
        self.turn_count = 1
        self.lightning_flash_square = None
        self.lightning_flash_timer = 0
        
        # Auto-trigger counters
        self.wind_counter = 0
        self.lightning_counter = 0
        self.freeze_counter = 0
        
    def handle_click(self, pos):
        x, y = pos
        
        # Check if click is on board
        if BOARD_OFFSET_X <= x < BOARD_OFFSET_X + BOARD_SIZE * SQUARE_SIZE and \
           BOARD_OFFSET_Y <= y < BOARD_OFFSET_Y + BOARD_SIZE * SQUARE_SIZE:
            col = (x - BOARD_OFFSET_X) // SQUARE_SIZE
            row = (y - BOARD_OFFSET_Y) // SQUARE_SIZE
            
            if self.board.selected_piece:
                if (row, col) in self.board.valid_moves:
                    if self.board.move_piece(row, col):
                        self.turn_count += 1
                        self.check_auto_triggers()
                    else:
                        self.board.select_piece(row, col)
                else:
                    self.board.select_piece(row, col)
            else:
                self.board.select_piece(row, col)
    
    def check_auto_triggers(self):
        """Check if any disasters should be triggered based on turn count"""
        self.wind_counter += 1
        self.lightning_counter += 1
        self.freeze_counter += 1
        
        if self.freeze_counter >= 3:
            self.board.apply_freeze_disaster()
            self.freeze_counter = 0
        
        if self.wind_counter >= 5:
            self.board.apply_wind_disaster()
            self.wind_timer = 30
            self.wind_counter = 0
        
        if self.lightning_counter >= 10:
            flash_square = self.board.apply_lightning_strike()
            if flash_square is not None:
                self.lightning_flash_square = flash_square
                self.lightning_flash_timer = 30
            self.lightning_counter = 0
    
    def draw_board(self):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x = BOARD_OFFSET_X + col * SQUARE_SIZE
                y = BOARD_OFFSET_Y + row * SQUARE_SIZE
                
                # Get biome for this square and choose color accordingly
                biome = self.board.get_biome(row, col)
                if biome == "ice":
                    color = ICE_BIOME_LIGHT if (row + col) % 2 == 0 else ICE_BIOME_DARK
                elif biome == "plains":
                    color = PLAINS_BIOME_LIGHT if (row + col) % 2 == 0 else PLAINS_BIOME_DARK
                elif biome == "stormy":
                    color = STORMY_BIOME_LIGHT if (row + col) % 2 == 0 else STORMY_BIOME_DARK
                else:
                    color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                
                pygame.draw.rect(self.screen, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))
                
                # Highlight selected piece
                if self.board.selected_piece == (row, col) and not self.board.is_in_blackout(row, col):
                    pygame.draw.rect(self.screen, SELECTED, (x, y, SQUARE_SIZE, SQUARE_SIZE), 5)
                
                # Highlight valid moves
                if (row, col) in self.board.valid_moves and not self.board.is_in_blackout(row, col):
                    pygame.draw.circle(self.screen, HIGHLIGHT, (x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2), 10)
                
                # Show frozen indicator
                if self.board.is_piece_frozen(row, col):
                    pygame.draw.rect(self.screen, (0, 0, 255), (x, y, SQUARE_SIZE, SQUARE_SIZE), 3)
        
        # Draw coordinate labels
        coord_font = pygame.font.Font(None, 20)
        # Column labels (A-H)
        for col in range(BOARD_SIZE):
            label = chr(ord('A') + col)
            text = coord_font.render(label, True, BLACK)
            x = BOARD_OFFSET_X + col * SQUARE_SIZE + SQUARE_SIZE // 2
            y = BOARD_OFFSET_Y + BOARD_SIZE * SQUARE_SIZE + 5
            text_rect = text.get_rect(center=(x, y))
            self.screen.blit(text, text_rect)
        
        # Row labels (8-1, from top to bottom)
        for row in range(BOARD_SIZE):
            label = str(8 - row)
            text = coord_font.render(label, True, BLACK)
            x = BOARD_OFFSET_X - 25
            y = BOARD_OFFSET_Y + row * SQUARE_SIZE + SQUARE_SIZE // 2
            text_rect = text.get_rect(center=(x, y))
            self.screen.blit(text, text_rect)

    def draw_blackout_overlay(self):
        """Cover the active blackout quadrant in black."""
        if not self.board.blackout_active:
            return

        bounds = self.board.get_blackout_bounds()
        if bounds is None:
            return

        min_row, max_row, min_col, max_col = bounds
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                x = BOARD_OFFSET_X + col * SQUARE_SIZE
                y = BOARD_OFFSET_Y + row * SQUARE_SIZE
                pygame.draw.rect(self.screen, BLACK, (x, y, SQUARE_SIZE, SQUARE_SIZE))

    def draw_lightning_overlay(self):
        """Flash the struck square yellow for a short time."""
        if self.lightning_flash_timer <= 0 or self.lightning_flash_square is None:
            return

        row, col = self.lightning_flash_square
        x = BOARD_OFFSET_X + col * SQUARE_SIZE
        y = BOARD_OFFSET_Y + row * SQUARE_SIZE
        flash_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        flash_surface.fill((255, 255, 0, 140))
        self.screen.blit(flash_surface, (x, y))
        self.lightning_flash_timer -= 1
        if self.lightning_flash_timer <= 0:
            self.lightning_flash_square = None
    
    def draw_pieces(self):
        # Unicode chess symbols
        white_pieces = {
            PieceType.PAWN: "♙",
            PieceType.ROOK: "♖",
            PieceType.KNIGHT: "♘",
            PieceType.BISHOP: "♗",
            PieceType.QUEEN: "♕",
            PieceType.KING: "♔"
        }
        black_pieces = {
            PieceType.PAWN: "♟",
            PieceType.ROOK: "♜",
            PieceType.KNIGHT: "♞",
            PieceType.BISHOP: "♝",
            PieceType.QUEEN: "♛",
            PieceType.KING: "♚"
        }
        
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board.board[row][col]
                if piece:
                    x = BOARD_OFFSET_X + col * SQUARE_SIZE + SQUARE_SIZE // 2
                    y = BOARD_OFFSET_Y + row * SQUARE_SIZE + SQUARE_SIZE // 2
                    
                    # Select the right symbol set based on piece color
                    symbols = white_pieces if piece.color == PieceColor.WHITE else black_pieces
                    symbol = symbols[piece.piece_type]
                    
                    # Render the symbol
                    text = self.piece_font.render(symbol, True, BLACK)
                    text_rect = text.get_rect(center=(x, y))
                    self.screen.blit(text, text_rect)
    
    def draw_ui(self):
        panel_x = BOARD_OFFSET_X + BOARD_SIZE * SQUARE_SIZE + 30
        panel_y = BOARD_OFFSET_Y
        panel_width = WINDOW_WIDTH - panel_x - 30
        panel_height = BOARD_SIZE * SQUARE_SIZE

        pygame.draw.rect(self.screen, (235, 235, 235), (panel_x - 15, panel_y, panel_width + 10, panel_height))
        pygame.draw.rect(self.screen, DARK_GRAY, (panel_x - 15, panel_y, panel_width + 10, panel_height), 2)

        # Draw turn info
        player_name = "WHITE" if self.board.current_player == PieceColor.WHITE else "BLACK"
        status_text = self.font.render(f"Turn {self.turn_count}", True, BLACK)
        player_text = self.font.render(f"{player_name} TO MOVE", True, BLACK)
        self.screen.blit(status_text, (panel_x, panel_y + 10))
        self.screen.blit(player_text, (panel_x, panel_y + 34))

        # Draw game state messages (check, checkmate, stalemate)
        if self.board.game_message:
            color = RED if "Checkmate" in self.board.game_message or "Check!" in self.board.game_message else GRAY
            message_text = self.small_font.render(self.board.game_message, True, color)
            self.screen.blit(message_text, (panel_x, panel_y + 60))

        if self.board.blackout_active:
            blackout_text = self.small_font.render(f"Blackout active: {self.board.blackout_turns_left} turns left", True, RED)
            self.screen.blit(blackout_text, (panel_x, panel_y + 80))

        if self.wind_timer > 0:
            effect_text = self.small_font.render("WIND BLOWING!", True, RED)
            self.screen.blit(effect_text, (panel_x, panel_y + 125))
            self.wind_timer -= 1

        return None
    
    def run(self):
        running = True
        
        while running:
            self.clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
            
            # Draw everything
            self.screen.fill(WHITE)
            self.draw_board()
            self.draw_pieces()
            self.draw_lightning_overlay()
            self.draw_blackout_overlay()
            self.draw_ui()
            
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
