"""Chess program that either accepts human player's input moves or 
randomly selects moves"""

import random, copy, time, cProfile

not_on_board = [10*i for i in range(2,10)] + [10*i+9 for i in range(2,10)]
on_board = [square for square in range(20,100) if square not in not_on_board]

def initialise_board():
    """creates initial chess position"""
    board = [0]*120 #empty chess board
    
    edges = range(20)
    edges += range(100,120)
    edges += [10 * n for n in range(2,10)]
    edges += [10 * n + 9 for n in range(2,10)]
    #print edges
    
    for i in edges:
        board[i] = 100
    
    #fill with white pieces (initial position)
    board[21] = 4
    board[22] = 2
    board[23] = 3
    board[24] = 5
    board[25] = 6
    board[26] = 3
    board[27] = 2
    board[28] = 4
    for i in range(31,39):
        board[i] = 1
        
    #fill with black pieces (initial position)    
    board[91] = -4
    board[92] = -2
    board[93] = -3
    board[94] = -5
    board[95] = -6
    board[96] = -3
    board[97] = -2
    board[98] = -4
    for i in range(81,89):
        board[i] = -1
    return board

def print_board(board):
    """prints board using numbers"""
    for i in range(12):
        j = 11-i
        print board[10*j:10*(j+1)]

def print_board2(board):
    """prints board using letters and without the edges"""
    d = {-6: "bK",
    -5: "bQ",
    -4: "bR",
    -3: "bB",
    -2: "bN",
    -1: "bP",
    0: "  ",
    1: "wP",
    2: "wN",
    3: "wB",
    4: "wR",
    5: "wQ",
    6: "wK"}
    for i in range(8):
        j = 9-i
        line = str(j-1)+" |"
        for k in range(10*j+1,10*j+9):
            line += d[board[k]]
            line += " |"
        print line
    print "   a   b   c   d   e   f   g   h"

col_dict = {1: "a", 2: "b", 3: "c", 4: "d", 5: "e", 6: "f", 7: "g", 8: "h"}
col_dict_ = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8}
piece_dict = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}
piece_dict_ = {"P": 1, "N": 2, "B": 3, "R": 4, "Q": 5, "K": 6}

def printable_move(move):
    """converts internal square representation to common chess notation"""
    start = move[0]
    finish = move[1]
    start_col = col_dict[start % 10]
    start_row= str(start/10-1)
    finish_col = col_dict[finish % 10]
    finish_row = str(finish/10 - 1)
    s = start_col + start_row + "-" + finish_col + finish_row
    if len(move) == 2:
        return s
    else:
        promoted_to = move[2]
        return s + piece_dict[abs(promoted_to)]
    

def calc_offsets(piece,pos,board,move_seq,sgn,with_castling = True):
    """determine potential offsets for a given piece type on a certain position on the board"""
    #print "piece=", piece
    #print "pos=",pos
    #print "sgn=",sgn
    
    #knight
    if piece == 2:
        if pos % 10 == 1: #knight on a file
            offsets = [21,19,12,-21,-19,-8]
        elif pos % 10 == 8: #knight on h file
            offsets = [21,19,8,-21,-19,-12]
        else:
            offsets = [21,19,8,12,-21,-19,-8,-12] #knight somewhere else
    #king
    elif piece == 6:    
        offsets = [-11,-10,-9,-1,1,9,10,11]
        if with_castling:
            #check that king has not moved, rook is on original square, \
            #all squares inbetween are empty, king is not in check
            if sgn == 1:
                colour = "white"
                sq = 25
            else:
                colour = "black"
                sq = 95
            if sq not in [move[0] for move in move_seq]\
            and not king_hanging(board,move_seq,colour,None):
                #kingside castling
                if abs(board[sq+3]) == 4\
                and board[sq+1] == 0 and board[sq+2] == 0:\
                #check that king wouldn't castle over attacked square
                    if not king_hanging(board,move_seq,colour,(sq,sq+1))\
                    and not king_hanging(board,move_seq,colour,(sq,sq+2)):
                        #add castling to offsets
                        offsets.append(2)
                #queenside castling
                if abs(board[sq-4]) == 4\
                and board[sq-1] == 0 and board[sq-2] and board[sq-3] == 0:\
                    #check that king wouldn't castle over attacked square
                    if not king_hanging(board,move_seq,colour,(sq,sq-1))\
                    and not king_hanging(board,move_seq,colour,(sq,sq-2))\
                    and not king_hanging(board,move_seq,colour,(sq,sq-3)):
                        #add castling to offsets
                        offsets.append(-2)
    #pawn
    elif piece == 1:
        a = 56 - sgn*25
        b = 64 - sgn*25
        offsets = []
        if board[pos + sgn*10] == 0:
            offsets.append(sgn*10)
            if pos in range(a,b) and board[pos + sgn*20] == 0:
                offsets.append(sgn*20)
        #if can capture diagonally or en passant, add offset
        if len(move_seq) > 0:
            c = 56 + 5*sgn
            d = 64 + 5*sgn
            #topleft or bottomright
            if sgn * board[pos + sgn*9] < 0 \
            or (pos in range(c,d) and move_seq[-1] == (pos+sgn*19,pos-sgn) \
            and board[pos-sgn] == -1*sgn): #pawn to the left
                offsets.append(sgn*9)
            #topright or bottomright
            if sgn * board[pos + sgn*11] < 0 \
            or (pos in range(c,d) and move_seq[-1] == (pos+sgn*21,pos+sgn) \
            and board[pos+sgn] == -1*sgn): #pawn to the right
                offsets.append(sgn*11)
    #bishop
    elif piece == 3:
        offsets = []
        directions = [11,-11,9,-9]
        #11 is topright direction, -11 is bottomleft, 9 is topleft, -9 is bottomright
        for d in directions:
            i = 1
            while sgn * board[pos + d*i] <= 0:
                offsets.append(d*i)
                if sgn * board[pos + d*i] < 0:
                    break
                else:
                    i += 1
    #rook
    elif piece == 4:
        offsets = []
        directions = [10,-10,1,-1]
        #10 is up, -10 is down, 1 is right, -1 is left
        for d in directions:
            i = 1
            while sgn*board[pos + d*i] <= 0:
                offsets.append(d*i)
                if sgn*board[pos + d*i] < 0:
                    break
                else:
                    i += 1
    #queen
    elif piece == 5:
        offsets = []
        directions = [11,-11,9,-9, 10,-10,1,-1] #bishop and rook directions
        for d in directions:
            i = 1
            while sgn*board[pos + d*i] <= 0:
                offsets.append(d*i)
                if sgn*board[pos + d*i] < 0:
                    break
                else:
                    i += 1
    return offsets  

def king_hanging(board,move_seq,colour,move):
    """checks whether, after colour's move, colour's king can be captured in a given 
    position by the other player"""
    #print "calling king_hanging with move=",move,"colour=",colour
    if colour == "white":
        sgn = 1
    else:
        sgn = -1
    board_copy = copy.copy(board)
    make_move(board_copy,move_seq,move)
    #if the move list has a move with target square the sgn's king, return True
    kings_square = board_copy.index(sgn*6)
    
    #check whether new square attacked: check around king whether there are pawns diagonally opposite or knights an L-offset away or king adjacent
    #then check along rows/columns (rooks, queens) and diagonals (bishops, queens) until hit a piece
    
    for direction in [10,-10,-1,1]: #check rows and colums (up, down, left, right)
        offset = direction
        new_sq = kings_square+offset
        while new_sq in on_board:
            if board_copy[new_sq] in (-4*sgn,-5*sgn):
                return True
            elif board_copy[new_sq] != 0:
                break
            else:
                offset += direction
                new_sq = kings_square+offset

    for direction in [9,-9,11,-11]: #check diagonals (up left, down right, up right, down left)
        offset = direction
        new_sq = kings_square+offset
        while new_sq in on_board:
            if board_copy[new_sq] in (-3*sgn,-5*sgn):
                return True
            elif board_copy[new_sq] != 0:
                break
            else:
                offset += direction
                new_sq = kings_square+offset
    
    for offset in [sgn*9,sgn*11]: #check pawns
        new_sq = kings_square+offset
        if board_copy[new_sq] == -1*sgn:
            return True
    
    for offset in [-11,-10,-9,-1,1,9,10,11]: #check king
        new_sq = kings_square + offset
        if board_copy[new_sq] == -6*sgn:
            return True
    
    #check knights    
    if kings_square % 10 == 1: #king on a file
        offsets = [21,19,12,-21,-19,-8]
    elif kings_square % 10 == 8: #king on h file
        offsets = [21,19,8,-21,-19,-12]
    else:
        offsets = [21,19,8,12,-21,-19,-8,-12] #king somewhere else
    for offset in offsets:
        new_sq = kings_square + offset
        if board_copy[new_sq] == -2*sgn:
            return True 

    #if no flag is raised
    return False 

def make_move_list(board,move_seq,colour,check_for_king_hanging = True, with_castling = True):
    """list legal moves in a given position in the form: (old field,new field)
    for white: colour = "white", for black: colour = "black"
    need to be able to exclude castling moves so as to avoid 
    infinite recursion when checking whether castling puts the king in check 
    (opponent's castling needn't be considered as a response to determine 
    whether king is in check after castling)"""
    move_list=[]
    if colour == "white":
        sgn = 1
    else:
        sgn = -1
    #print "calling make_move_list, colour=",colour,"check_for_king_hanging=",check_for_king_hanging
    
    pairs = [(pair[0],abs(pair[1])) for pair in enumerate(board) if pair[0] in on_board and sgn*pair[1] > 0]
    #print pairs
    for pos, piece in pairs:
        offsets = calc_offsets(piece,pos,board,move_seq,sgn,with_castling)
        #print "pos=",pos,"piece=",piece,"offsets=",offsets
        potential_targets = [pos + offset for offset in offsets]
        potential_targets = [target for target in potential_targets if target in on_board]
        if piece != 1: #pawns already checked
            targets = [target for target in potential_targets if sgn*board[target] <= 0]
        else:
            targets = potential_targets
        #if pawn moves to last row (8th or 1st), promote to N/B/R/Q
        if piece == 1:
            for target in targets:
                if target not in range(21,29)+range(91,99):
                    #print "appending: ", (pos,target)
                    move_list.append((pos,target))
                else:
                    for promoted_to in (2,3,4,5):
                        #print "appending: ", (pos,target)
                        move_list.append((pos,target,promoted_to))
        else:
            for target in targets:
                #print "appending: ", (pos,target)
                move_list.append((pos,target))
        #print "move_list=",move_list
                
    if check_for_king_hanging:
        for move in copy.copy(move_list):
            #if after move own king is in check, remove this move from the move list
            #print "checking whether king hanging after move=",move
            #print_board2(board)
            if king_hanging(board,move_seq,colour,move):
                #print "king hanging after ",move," so removing"
                move_list.remove(move)
    return move_list
    
def make_move(board,move_seq,move):
    """execute a move on the board"""
    if move is not None:
        #if pawn promotes
        if len(move) > 2:
            if board[move[0]] > 0:
                sgn = 1
            else:
                sgn = -1
            board[move[1]] = sgn * move[2]
        #elif pawn takes en passant (i.e. pawn moves one square diagonally to an empty square)
        elif abs(board[move[0]]) == 1 and abs(move[1]-move[0]) in (9,11) and board[move[1]] == 0:   
            board[move[1]] = board[move[0]]
            captured_pawn_on = move_seq[-1][1]
            board[captured_pawn_on] = 0
        #elif castling
        elif abs(board[move[0]]) == 6 and abs(move[1]-move[0]) in (2,3):
            board[move[1]] = board[move[0]] #king move
            #rook move
            if move[0] == 25:
                if move[1]-move[0] == 2: #white kingside
                    board[26] = 4
                    board[28] = 0
                else: #white queenside
                    board[24] = 4
                    board[21] = 0
            else:
                if move[1]-move[0] == 2: #black kingside
                    board[96] = 4
                    board[98] = 0
                else: #black queenside
                    board[94] = 4
                    board[91] = 0   
        else:
            board[move[1]] = board[move[0]]
        board[move[0]] = 0

def play_game(num_moves,white,black,verbose=True):
    """if white/black = random, computer makes random choice
    if white/black = human, computer expects human player to make inputs
    maximum number of moves is num_moves"""
    board = initialise_board()
    if verbose:
            print_board2(board)
    num = 1
    turn = "white"
    move_seq = []
    fifty_move_counter = 0
    old_num_pieces = None
    num_pieces = 32
    pawn_moved = None
    position_hashes = dict()
    while num <= num_moves:
        h = hash(tuple(board)+tuple([turn]))
        if verbose:
            print "hash=",h
        if h not in position_hashes:
            position_hashes[h] = 1
        else:
            position_hashes[h] += 1
        if verbose:
            print "Turn =",turn, "Move number =", num
        possible_moves = make_move_list(board,move_seq,turn)
        if verbose:
            move_string = "Possible moves"
            for move in possible_moves:
                move_string += (", " + printable_move(move))
            print move_string
        if len(possible_moves) == 0: #no possible moves
            #if in check, checkmate
            if king_hanging(board,move_seq,turn,None):
                print turn, "is checkmate!"
            #else stalemate
            else:
                print turn, "is stalemate!"
            break
        
        #threefold repetition"
        #ignores possible hash collision. to deal with this, store list of historic
        #board positions and in the case of triple occurence of a hash value,
        #do another check of the full board positions
        if position_hashes[h] == 3:
            print "draw due to threefold repetition"
            break
            
        #if too little material on board, draw (K-K,KN-K,K-KN,KB-K,K-KB)
        if num_pieces == 2:
            print "Draw due to insufficient material!"
            break
        if num_pieces == 3:
            pieces = [abs(board[square]) for square in on_board if board[square] != 0]
            if 2 in pieces or 3 in pieces:
                print "Draw due to insufficient material!"
                break
                
        #50 move rule        
        #print "old_num_pieces=",old_num_pieces, "num_pieces=",num_pieces
        #print "pawn_moved=",pawn_moved
        if num_pieces == old_num_pieces and not pawn_moved:
            fifty_move_counter += 1
            if fifty_move_counter >= 100:
                print "Draw due to 50 move rule"
                break
        else:
            fifty_move_counter = 0        
                
        if (turn == "white" and white == "random") or (turn == "black" and black == "random"):
            choice = random.choice(possible_moves)
        else:
            valid = False
            while not valid: 
                m = input("make move ").split(",") #input move as a string in the form: "e2,e4" or "d7,d8,Q"
                #convert start and finish square to internal representation
                start_col = col_dict_[m[0][0]]
                start_sq = (int(m[0][1]) + 1) * 10 + start_col
                finish_col = col_dict_[m[1][0]]
                finish_sq = (int(m[1][1]) + 1) * 10 + finish_col
                if len(m) > 2:
                    choice = (start_sq,finish_sq,piece_dict_[m[2]])
                else:
                    choice = (start_sq,finish_sq)
                print choice
                if choice in possible_moves:
                    valid = True
                else:
                    print "invalid move"
        move_seq.append(choice)
        if verbose:
            print "Move =", printable_move(choice)
       
        #50 move rule: updating counter if no pawn has moved and a piece has not been captured 
        pawn_moved = (abs(board[choice[0]]) == 1)
        old_num_pieces = num_pieces
        make_move(board,move_seq,choice) #execute move
        num_pieces = sum(1 if board[square] != 0 else 0 for square in on_board) 
        
        if verbose:
            print_board2(board)
        if turn == "white":
            turn = "black"
        else:
            turn = "white"
        num += 1
        if verbose:
            print "\n"
    if verbose:
            seq_string = "All moves"
            i = 1
            for move in move_seq:
                seq_string += (" " + str(i) + "." + printable_move(move))
                i += 1
            print seq_string

def setup_position(pos):
    """sets up an arbitrary board position based on user inputs and checks legality.
    if pos is None, piece-by-piece user input, otherwise list of two strings of the form
    ['Pa2,Pb2,Ra1','Pa7,Ke8'] is expected."""
    
    board = [0]*120 #empty chess board
    
    edges = range(20)
    edges += range(100,120)
    edges += [10 * n for n in range(2,10)]
    edges += [10 * n + 9 for n in range(2,10)]
    #print edges
    
    for i in edges:
        board[i] = 100
    
    if pos == None:   
        #fill with white pieces 
        #user inputs in the form: "Ke4". If stop, enter "stop"    
        print "Enter white pieces\n"
        while True:
            try:
                p = input("Enter white piece ")
                if p == "stop":
                    break
                piece,col,row = list(p)
                piece = piece_dict_[piece]
                col = col_dict_[col]
                square = (int(row) + 1) * 10 + col
                board[square] = piece
            except:
                print "bad input"
                
        #fill with black pieces     
        #user inputs in the form: "Ke4". If stop, enter "stop"    
        print "Enter black pieces\n"
        while True:
            try:
                p = input("Enter black piece ")
                if p == "stop":
                    break
                piece,col,row = list(p)
                piece = -1 * piece_dict_[piece]
                col = col_dict_[col]
                square = (int(row) + 1) * 10 + col
                board[square] = piece
            except:
                print "bad input"
    else:
        white = pos[0].split(",")
        black = pos[1].split(",")
        for w in white:
            piece,col,row = list(w)
            piece = piece_dict_[piece]
            col = col_dict_[col]
            square = (int(row) + 1) * 10 + col
            board[square] = piece
        for b in black:
            piece,col,row = list(b)
            piece = -1 * piece_dict_[piece]
            col = col_dict_[col]
            square = (int(row) + 1) * 10 + col
            board[square] = piece
                      
    #check for legality
    
    #both sides have exactly one king"
    assert board.count(6) == 1 and board.count(-6) == 1
    #no pawns in first or last row
    assert not any(board[i] in (-1,1) for i in range(21,29)+range(91,99))    
    
    return board

def test_suite():
    """tests play_game function"""
    
    
    #error-free execution of lots of random games
    time0 = time.time()
    for count in range(100):
        play_game(500,"random","random",verbose = False)
    time1 = time.time()
    print "total time elapsed = ",time1-time0,"seconds"
    
    

#play_game(200,'random','random',verbose = True)
#cProfile.run("test()")

#play_game(200,"human","human",verbose = True)

new_board = setup_position(['Pa2,Pb2,Ra1,Ke1','Pa7,Ke8'])
print_board2(new_board)