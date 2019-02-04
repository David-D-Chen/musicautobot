from fastai.text import *
from fastai.distributed import *
from fastai_data import *

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str, default='data/midi/midi_transcribe_v1_simple/')
parser.add_argument('--cache', type=str, default='tmp_clc')
parser.add_argument('--save', type=str, default='first_run')
parser.add_argument('--load', type=str, default=None)
parser.add_argument('--load_cache', type=str, default=None)
parser.add_argument("--local_rank", type=int)
parser.add_argument("--batch_size", type=int, default=256)
parser.add_argument("--bptt", type=int, default=500)
parser.add_argument('--half', action='store_true', help='Use half precision')
parser.add_argument('--wd', type=float, default=1e-3, help='weight decay for adam')
parser.add_argument('--epochs', type=int, default=5, help='num epochs')
parser.add_argument('--lr', type=float, default=1e-3, help='learning rate')
args = parser.parse_args()

if args.local_rank != 0:
    f = open('/dev/null', 'w')
    sys.stdout = f

torch.cuda.set_device(args.local_rank)
torch.distributed.init_process_group(backend='nccl', init_method='env://')

bs=args.batch_size
bptt=args.bptt
path = Path(args.path)
data = TextLMDataBunch.load(path, cache_name=args.cache, bs=bs, bptt=bptt)
data.valid_ds.x.processor[0] = TokenizeProcessor(tokenizer=MusicTokenizer())

learn = language_model_learner(data, drop_mult=1, clip=.5, bptt=bptt).distributed(args.local_rank)
if args.load:
    load_path = Path(args.path)/args.load_cache/learn.model_dir/f'{args.loadname}.pth'
    if device is None: device = data.device
    state = torch.load(load_path, map_location=device)
    get_model(learn.model).load_state_dict(state, strict=True)
learn.unfreeze()

learn.fit_one_cycle(args.epochs, args.lr, div_factor=25, moms=(0.7,0.5))
if args.local_rank == 0: learn.save(f'{args.cache}_{args.save}')
