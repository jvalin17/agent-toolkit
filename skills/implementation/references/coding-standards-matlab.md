# MATLAB Coding Standards

> Our synthesis of MathWorks style guidelines and community best practices. Follow the official MathWorks documentation for the authoritative source.
> Last verified: 2026-09-14

## Sources
- [MATLAB Style Guidelines 2.0 — Richard Johnson](https://www.mathworks.com/matlabcentral/fileexchange/46056-matlab-style-guidelines-2-0)
- [MathWorks MATLAB Programming Style Guide](https://www.mathworks.com/help/matlab/matlab_prog/program-files.html)
- [MATLAB Documentation — Code Quality](https://www.mathworks.com/help/matlab/code-quality.html)

## File Organization
```
+mypackage/              % package namespace folder
    MyClass.m            % @class in package (PascalCase)
    helperFunction.m     % one function per file (camelCase)
@MyClass/                % class folder (alternative)
    MyClass.m            % constructor
    myMethod.m           % one method per file
scripts/
    runAnalysis.m        % scripts are camelCase too
```

**Rules:**
- One function per file. Filename must match the primary function name exactly.
- Use `+packageName` folders for namespacing. Use `@ClassName` folders for complex classes. Keep files under ~200 lines.

## Naming
```matlab
% GOOD: descriptive, convention-correct
function result = computeMovingAverage(signal, windowSize)

MAX_ITERATIONS = 1000;          % constant: UPPER_SNAKE_CASE
DEFAULT_TOLERANCE = 1e-6;

numSamples = length(signal);    % variable: camelCase
isConverged = false;            % boolean reads as question

classdef SignalProcessor         % class: PascalCase

% BAD: vague, abbreviated, wrong case
function r = cma(s, w)          % what is cma? s? w?
n = length(s);                  % n tells us nothing
flag = false;                   % flag for what?
MYSIGNAL = [];                  % not a constant, wrong case
```

**Rules:**
- camelCase for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants.
- Booleans read as questions: `isValid`, `hasData`, `isEmpty`. Functions read as actions: `computeFFT`, `loadConfig`.
- No single-letter names except `i, j` in short loops (avoid if using complex numbers — they shadow `sqrt(-1)`).

## Vectorization
```matlab
% GOOD: vectorized operation
result = sum(data .^ 2);
mask = values > threshold;
filtered = values(mask);

% GOOD: implicit broadcasting (R2016b+)
distances = sqrt(sum((points - center) .^ 2, 2));

% BAD: unnecessary scalar loop
result = 0;
for k = 1:length(data)
    result = result + data(k)^2;   % just use sum(data.^2)
end

filtered = [];
for k = 1:length(values)
    if values(k) > threshold
        filtered(end+1) = values(k);   % growing AND loopy
    end
end
```

**Rules:**
- Use element-wise operators (`.*, ./, .^`) and logical indexing (`x(x > 0)`) over loops.
- Prefer built-ins (`sum`, `mean`, `max`, `any`, `all`, `cumsum`) over hand-rolled loops.
- Reserve loops for inherently sequential logic (recursive state, variable-length output per step).

## Preallocation
```matlab
% GOOD: preallocate before the loop
n = 10000;
results = zeros(1, n);
for k = 1:n
    results(k) = heavyComputation(k);
end

% GOOD: cell array preallocation
chunks = cell(1, numChunks);

% BAD: growing inside loop (reallocates every iteration)
results = [];
for k = 1:n
    results(end+1) = heavyComputation(k);   % O(n^2) copies
end
```

**Rules:**
- Always preallocate with `zeros`, `ones`, `nan`, `false`, or `cell` before loops.
- Use `NaN` as sentinel so unfilled entries are visible. Unknown size: preallocate generously then trim: `results(k+1:end) = []`.

## Error Handling
```matlab
% GOOD: validateattributes at entry, structured error ID
validateattributes(filePath, {'char','string'}, {'scalartext'}, mfilename, 'filePath');
if ~isfile(filePath)
    error('myPkg:loadFile:fileNotFound', 'File not found: %s', filePath);
end

% GOOD: inputParser for complex signatures
p = inputParser;
addRequired(p, 'signal', @(x) isnumeric(x) && isvector(x));
addParameter(p, 'method', 'hamming', @ischar);
parse(p, signal, varargin{:});

% BAD: silent catch, no ID
try; data = load(filePath); catch; data = []; end  % swallowed error
error('Something went wrong');                      % no ID, no context
```

**Rules:**
- Use message IDs: `'packageName:functionName:issueType'` — enables selective suppression.
- Validate at function entry with `validateattributes` or `inputParser`, not scattered `if` checks.
- Never silent-catch. Log with `warning(...)` or rethrow: `catch ME; rethrow(ME); end`.

## Memory
```matlab
% GOOD
A = sparse(rows, cols, values, m, n);   % sparse for mostly-zero data
result = A * x;                          % stays sparse through multiply
bigMatrix = computeIntermediateResult();
finalResult = reduce(bigMatrix);
clear bigMatrix;                         % free before next allocation
x = normalize(x);                        % reuse variable, avoid extra copy

% BAD: dense matrix for sparse problem — 800 MB for 99%-zero data
A = zeros(10000, 10000);
for k = 1:nnz
    A(rows(k), cols(k)) = vals(k);
end
```

**Rules:**
- Use `sparse` when density is below ~10% (`nnz(A)/numel(A)`). `clear` large variables once done.
- Reassign in-place to avoid copies. Run `whos` to spot memory hogs early.

## Plotting
```matlab
% GOOD: explicit handles, fully labeled
fig = figure('Name', 'Signal Analysis');
ax = axes(fig);
plot(ax, timeVec, signal, 'b-', 'LineWidth', 1.5);
hold(ax, 'on');
plot(ax, timeVec, filtered, 'r--', 'LineWidth', 1.5);
hold(ax, 'off');
xlabel(ax, 'Time (s)'); ylabel(ax, 'Amplitude (V)');
title(ax, 'Raw vs Filtered Signal'); legend(ax, 'Raw', 'Filtered');

% BAD: implicit state, no labels
figure; plot(t, s); hold on; plot(t, f); title('plot');
```

**Rules:**
- Always assign figure/axes handles. Never rely on `gcf`/`gca` — pass handles explicitly.
- Always pair `hold(ax, 'on')` with `hold(ax, 'off')` to prevent leaked hold state.
- Every axis needs `xlabel`, `ylabel`, descriptive `title`, and `legend` when multiple series.
- Use `exportgraphics(fig, 'out.pdf')` over `print` for resolution-independent output.

## Common Anti-Patterns
```matlab
% BAD: eval — opaque, unsearchable, injection risk
eval(['result = compute_' methodName '(x)']);
% GOOD: use function handles or a switch
methods = struct('fft', @computeFFT, 'wavelet', @computeWavelet);
result = methods.(methodName)(x);

% BAD: global variables
global sampleRate;
% GOOD: pass as argument or store in a struct/class

% BAD: hardcoded paths
data = load('/Users/alice/projects/data/raw.mat');
% GOOD: relative or config-driven
dataDir = fullfile(fileparts(mfilename('fullpath')), '..', 'data');
data = load(fullfile(dataDir, 'raw.mat'));

% BAD: magic numbers scattered through code
if numPoints > 4096
% GOOD: named constant at top of file
MAX_FFT_POINTS = 4096;
if numPoints > MAX_FFT_POINTS
```

**Rules:**
- Never `eval`. Use function handles or `struct` dispatch instead.
- No `global` variables. Pass state as arguments, structs, or class properties.
- No hardcoded paths. Use `mfilename('fullpath')` + `fullfile` or a config struct.
- No magic numbers. Define named constants at the top of the file.
