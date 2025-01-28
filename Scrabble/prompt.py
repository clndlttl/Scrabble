import logging
from litellm import completion
from dotenv import load_dotenv


SYSTEM_PROMPT = """
You are a Scrabble player. Here are the rules to Scrabble:

The user will give you a string containing up to 7 letters (called the "bank"), which are randomly drawn from a limited set (called the "pool").

You must place at least 1 and up to all 7 letters from your bank onto a common game board (a 15 x 15 grid) to spell valid words.
When you place your letters, at least 1 of them must touch a letter that was placed on the board on a previous turn.
The words that will be analyzed for validity will consist of a mix of the letters you place and previously-placed letters; therefore, it is not enough to identify a valid word in your bank and simply connect it to previously-placed letters!
In other words, each word you spell will include at least one letter placed on a previous turn, at any position in your new word.
When placing letters on the board, they must form a continuous horizontal or vertical line, which is to say that they must all be in the same row or column.

The goal of the game is to accumulate the most points before the game ends.
The game ends when either player runs out of letters in their bank and there are no more letters left in the pool.

Each letter of the alphabet is assigned a number of points:
a:1, b:3,  c:3, d:2, e:1, f:4, g:2, h:4, i:1, j:8, k:5, l:1, m:3, n:1, o:1, p:3, q:10, r:1, s:1, t:1, u:1, v:4, w:4, x:8, y:4, z:10
It is smart to play words with less-frequently used letters such as 'j', 'q', 'x', and 'z', because they are worth more points.

The user will also present you with the board state encoded as a string.
The string will contain 15 lines, each with 15 characters.
Each character indicates the state of that space on the board.

If the character is a letter in the alphabet, that means that space is occupied by a letter played on a previous turn.
A new letter cannot replace it, but it's letter value will still contribute to new words played off it.

Else, the character represents a free space and will be one of the following:
'.': adds no bonus to the value of the letter placed here,
'#': doubles the value of the letter placed here,
'@': triples the value of the letter placed here,
'%': doubles the value of any word that overlaps with this space,
'$': triples the value of any word that overlaps with this space.

Here is an example of board that you may encounter, in which has the word 'seek' already played on it:
$··#···$···#··$
·%···@···@···%·
··%···#·#···%··
#··%···#···%··#
····%·····%····
·@···@···@···@·
··#···#·#···#··
$··#···seek#··$
··#···#·#···#··
·@···@···@···@·
····%·····%····
#··%···#···%··#
··%···#·#···%··
·%···@···@···%·
$··#···$···#··$

Choose a move that maxmizes your score. Please format your move using this scheme:

<move>
row,column,letter
row,column,letter
...
</move>

It is very important that you surround your move in <move> and </move> tags.
Rows and columns should be 0-indexed, with the top-left corner of the board corresponding to 0,0.

For example, given the example board above, and assuming your bank is 'crohesn', and good move would be to place the word 'shocker', like so:
<move>
3,10,s
4,10,h
5,10,o
6,10,c
8,10,e
9,10,r
</move>

Notice here that this move utilizes the already-placed letter 'k' at space 7,10 and thus does not need to include it in the move specification.
Notice also that the 'h' is placed on a '%' space, which doubles the value of the word as a whole.

Given the same example board and bank, you might be tempted to spell the word 'heron' in this move:
<move>
5,7,h
6,7,e
8,7,r
9,7,o
10,7,n
</move>

However, while 'heron' is a valid word, this move actualy spells 'hesron' as it connects to the previously-played 's' at 7,7; 'hesron' is not a valid word.
"""

USER_PROMPT = """
Here's the board:

{board}

Here is your bank:

{bank}

Make your move.
You must spell real words only, and no proper nouns.
Each letter in your bank can only be used once.

{nudge}
"""

USER_NUDGE = """
----------
On a previous attempt, your move was:
{nudge}

However, this move was invalid because:
{error}

Please avoid these errors this time! Good luck!!!
"""


def buildNudge(move: list[tuple[int, int,str]], errors: list[str]) -> str:
    n = '<move>\n'
    for tup in move:
        n += f'{tup[0]},{tup[1]},{tup[2]}\n'
    n += '</move>\n'

    e = ',\n'.join(errors)

    rv = USER_NUDGE.format(nudge=n, error=e)
    return rv


def parse_move(move_text: str) -> list[tuple[int, int, str]]:
    """
    Parse a move string containing <move>...</move> tags into a list of (row, col, letter) tuples.

    Example input:
    <move>
    1,1,w
    1,2,a
    1,3,r
    </move>

    Returns: [(1, 1, 'w'), (1, 2, 'a'), (1, 3, 'r')]
    """
    # Extract content between <move> tags
    start = move_text.find("<move>") + len("<move>")
    end = move_text.find("</move>")
    if start == -1 or end == -1:
        return []

    content = move_text[start:end].strip()

    # Parse each line into a tuple
    move_list = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Parse "row,col: tile" format
        play = line.split(",")

        move_list.append((int(play[0]), int(play[1]), play[2]))

    return move_list


def AIPlayer(board: str, bank: str, nudge: str, logger: logging.Logger) -> list[tuple[int,int,str]]:

    load_dotenv()

    messages = [
        {
         "role": "system",
         "content": SYSTEM_PROMPT
        },
        {
         "role": "user",
         "content": USER_PROMPT.format(board=board, bank=bank, nudge=nudge)
        }
    ]

    response = completion(
        model='openai/o1-mini',
        messages=messages
    )

    reply = response.choices[0].message.content
    logger.debug('AI raw: %s', reply)

    moves = parse_move(reply)
    logger.debug('AI parsed: %s', moves)

    return moves


if __name__ == "__main__":

    load_dotenv()

    board = """
$··#···$···#··$
·%···@···@···%·
··%···#·#···%··
#··%···#···%··#
····%·····%····
·@···@···@···@·
··#···#·#···#··
$··#···seek#··$
··#···#·#···#··
·@···@···@···@·
····%·····%····
#··%···#···%··#
··%···#·#···%··
·%···@···@···%·
$··#···$···#··$
"""
    bank = 'crohesn'

    #move = AIPlayer(board, bank)
    #print(move)

