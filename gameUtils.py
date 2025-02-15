letterValues = {
    'a':1, 'b':3,  'c':3, 'd':2, 'e':1,
    'f':4, 'g':2,  'h':4, 'i':1, 'j':8,
    'k':5, 'l':1,  'm':3, 'n':1, 'o':1,
    'p':3, 'q':10, 'r':1, 's':1, 't':1,
    'u':1, 'v':4,  'w':4, 'x':8, 'y':4, 'z':10
}


def isLetter(char):
    return char not in ['.','#','@','%','$','*']


def isAdjacent(board: list[list[str]], row: int, col: int):
    nonletters = ['.','#','@','%','$','*']
    # left
    if col > 0 and isLetter(board[row][col-1]):
        return True
    # right
    if col < 14 and isLetter(board[row][col+1]):
        return True
    # up
    if row > 0 and isLetter(board[row-1][col]):
        return True
    # down
    if row < 14 and isLetter(board[row+1][col]):
        return True
    return False


def getFlatIndex(row, col):
    return 15*row + col


def findWords(mat: list[list[str]], attemptList: list[tuple[int,int,str]], errorList: list[str]):

    words = {}
    isStar = False
    isAdj = False

    for letter in attemptList:

        # build a set of attempt locations
        attemptIndices = { getFlatIndex(tup[0],tup[1]) : tup[2] for tup in attemptList }
        
        # letter is a tuple of (rowIdx, colIdx, letter)
        row = letter[0]
        col = letter[1]

        # check for board adjacency first
        isAdj |= isAdjacent(mat, row, col)
 
        # what space does this letter cover?
        space = mat[row][col]
        if space == '*':
            isStar = True

        # look for a horizontal word
        w = []
        hash = 0
        # rewind to start of word
        colStart = col
        while colStart > 0 and (isLetter( mat[row][colStart-1] ) or getFlatIndex(row, colStart-1) in attemptIndices):
            colStart -= 1
        # add first letter, noting if it's already there or new
        fi = getFlatIndex(row,colStart)
        hash += fi
        if fi in attemptIndices:
            w.append( (attemptIndices[fi], mat[row][colStart]) )
        else:
            w.append( (mat[row][colStart], None) )
        # read out the word
        colEnd = colStart
        while colEnd < 14 and (isLetter( mat[row][colEnd+1] ) or (getFlatIndex(row,colEnd+1) in attemptIndices)):
            colEnd += 1
            fi = getFlatIndex(row,colEnd)
            hash += fi
            if getFlatIndex(row,colEnd) in attemptIndices:
                w.append( (attemptIndices[fi], mat[row][colEnd]) )
            elif isLetter( mat[row][colEnd] ):
                w.append( (mat[row][colEnd], None) )
            else:
                errorList.append('Word is not continuous.')
        if colEnd != colStart:
            words[hash] = w

        # look for a vertical word
        w = []
        hash = 0
        # rewind to start of word
        rowStart = row
        while rowStart > 0 and (isLetter( mat[rowStart-1][col] ) or getFlatIndex(rowStart-1, col) in attemptIndices):
            rowStart -= 1
        # add first letter
        fi = getFlatIndex(rowStart,col)
        hash += fi
        if getFlatIndex(rowStart,col) in attemptIndices:
            w.append( (attemptIndices[fi], mat[rowStart][col]) )
        else:
            w.append( (mat[rowStart][col], None) )
        # read out the word
        rowEnd = rowStart
        while rowEnd < 14 and (isLetter( mat[rowEnd+1][col]) or (getFlatIndex(rowEnd+1,col) in attemptIndices)):
            rowEnd += 1
            fi = getFlatIndex(rowEnd,col)
            hash += fi
            if getFlatIndex(rowEnd,col) in attemptIndices:
                w.append( (attemptIndices[fi], mat[rowEnd][col]) )
            elif isLetter( mat[rowEnd][col] ):
                w.append( (mat[rowEnd][col], None) )
            else:
                errorList.append('Word is not continuous.')
        if rowEnd != rowStart:
            words[hash] = w
    
    return words, isStar, isAdj