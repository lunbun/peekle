from .. import il

class TransformPass:
    def __init__(self, name):
        self.name = name

    def run(self, program: il.Program) -> bool:
        raise NotImplementedError()

    def __str__(self):
        return self.name

class TransformManager:
    def __init__(self):
        self.passes: list[TransformPass] = []

    def add(self, pass_: TransformPass):
        self.passes.append(pass_)

    def run(self, program: il.Program, maxPasses: int = -1) -> int:
        modified = True
        n = 0
        while modified:
            modified = False
            for pass_ in self.passes:
                modified |= pass_.run(program)

            n += 1
            if maxPasses != -1 and n >= maxPasses:
                break
        
        return n
