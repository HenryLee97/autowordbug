from ast import literal_eval
from pathlib import Path
from torch.utils.data import DataLoader
import argparse
import sys
import torch
import torch.nn.functional as F
import torch.optim as optim

from src.data import Dataset
from src.data.preprocess import pad_sequences
import src.model as model_module

def make_args(args):
  return [literal_eval(arg) for arg in args]

def make_kwargs(kwargs):
  kwargs = [kwarg.split('=') for kwarg in kwargs]
  return {key: literal_eval(value) for key, value in kwargs}

def train_epoch(model, data_loader, optimizer, device):
  losses = []
  model.train()

  for inputs, targets in data_loader:
    inputs = inputs.long().to(device)
    targets = targets.to(device)

    outputs = model(inputs)
    loss = F.nll_loss(outputs, targets)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    losses.append(loss.cpu().item())

  return sum(losses) / len(losses) if len(losses) > 0 else 0

def main(argv=None):

  if not argv:
    argv = sys.argv[1:]
  
  parser = argparse.ArgumentParser(description='Training script.')
  # Training data.
  parser.add_argument('-d', '--data', type=str, metavar='<.csv>', required=True, help='Training data')
  parser.add_argument('-c', '--num-classes', type=int, metavar='<int>', required=True, help='Number of classes')
  parser.add_argument('--dictionary-size', type=int, default=20000, metavar='<int>', help='Number of words')
  parser.add_argument('--seq-len', type=int, default=500, metavar='<int>', help='Length of sequences to pad')
  parser.add_argument('--num-workers', type=int, default=1, metavar='<int>', help='Number of parellal nodes of preprocessing')
  # Model config.
  parser.add_argument('-m', '--model', type=str, default='WordRNN', metavar='<class>', help='Name of class in src.model')
  parser.add_argument('--args', type=str, nargs='*', default=[], metavar='<arg>', help='Arguments used when creating model')
  parser.add_argument('--kwargs', type=str, nargs='*', default=[], metavar='<key=arg>', help='Keyword arguments used when creating model')
  # Training config.
  parser.add_argument('--gpu', action='store_true', help='Use GPU if available')
  parser.add_argument('--epochs', type=int, default=10, metavar='<int>', help='Number of epochs')
  parser.add_argument('--batch-size', type=int, default=128, metavar='<int>', help='Batch size')
  parser.add_argument('-lr', '--learning-rate', type=float, default=0.0005, metavar='<float>', help='Learning rate')
  parser.add_argument('-p', '--save-path', type=str, default='model.pt', metavar='<.pt>', help='Path for trained model')

  args = parser.parse_args(argv)

  # Device setting.
  device = torch.device('cuda' if args.gpu and torch.cuda.is_available() else 'cpu')

  # Create model.
  model_cls = getattr(model_module, args.model)
  model = model_cls(*make_args(args.args), **make_kwargs(args.kwargs))
  model.to(device)

  # Create optimizer.
  optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
  
  # Load data.
  dataset = Dataset(args.data, args.dictionary_size, args.seq_len)
  data_loader = DataLoader(dataset, batch_size=args.batch_size, num_workers=args.num_workers, shuffle=True)

  # Start training.
  for epoch in range(args.epochs):
    print(f'Start epoch {epoch + 1}', end='', flush=True)
    loss = train_epoch(model, data_loader, optimizer, device)
    print(f'\rEpoch {epoch + 1} loss: {loss:6.4f}')

  # Save model.
  save_path = Path(args.save_path)
  save_path.parent.mkdir(parents=True, exist_ok=True)
  model.save(save_path, dataset.word_index)

if __name__ == '__main__':
  main()
