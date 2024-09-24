import argparse
import peekle

def main():
    parser = argparse.ArgumentParser(prog='Peekle CLI', description='Disassemble and decompile pickle files')
    parser.add_argument('input', type=str, help='The input file to disassemble/decompile')
    parser.add_argument('output', type=str, help='The output file to write the disassemble/decompiled code to')
    parser.add_argument('--il', action='store_true', help='Output the disassembled IL instead of decompiling')
    parser.add_argument('--no-analysis', action='store_true', help='Do not run any analysis passes')

    args = parser.parse_args()

    with open(args.input, 'rb') as f:
        disassembler = peekle.dis.Disassembler(f)
        program = disassembler.disassemble()

    if not args.no_analysis:
        transform = peekle.transform.TransformManager()
        transform.add(peekle.transform.ConstantValuePass())
        transform.add(peekle.transform.ConstantGlobalPass())
        transform.add(peekle.transform.ConstantGetItemPass())
        transform.add(peekle.transform.InlineMutableConstantPass())
        transform.add(peekle.transform.DeadCodePass())
        transform.add(peekle.transform.GlobalCallPass())
        transform.add(peekle.transform.InstanceDunderPass())
        transform.add(peekle.transform.ImportToGlobalPass())
        transform.add(peekle.transform.GlobalReductionPass())
        transform.add(peekle.transform.LocalsPass())
        n = transform.run(program, maxPasses=20)
        print(f'Analysis passes ran {n} time{"s" if n != 1 else ""}.')

    if args.il:
        src = str(program)
    else:
        codegen = peekle.codegen.CodeGenerator()
        src = codegen.generateSource(program)

    with open(args.output, 'wb') as f:
        f.write(src.encode('utf-8'))

    action = 'disassembled' if args.il else 'decompiled'
    if program.poison:
        print(f'{action.capitalize()} pickle file, some errors encountered.')
    else:
        print(f'Successfully {action} pickle file. Happy reversing!')

if __name__ == '__main__':
    main()
