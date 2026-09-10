function T = exportCountrySeries(cube, weights, opts)
% exportCountrySeries - Per-country ANNUAL SERIES for the dashboard
%
% regionalCountrySummary.m collapses the year axis, giving one recent mean and
% one slope per country. The dashboard's country profile cards need the series
% itself, so this keeps the year axis and writes a long-format table.
%
% Population-weighted within each country, matching regionalCountrySummary so
% the two products agree: the mean of AnnualMean over the trailing
% opts.recentYears here equals MeanAnnual_recent there.
%
% SYNTAX:
%   T = exportCountrySeries(cube, weights)
%   T = exportCountrySeries(cube, weights, opts)
%
% INPUTS:
%   cube    - from assembleBMEcube (or composeBestMethodCube)
%   weights - from computeGridWeights (provides ISO3, CountryName, w_pop)
%   opts    - (optional):
%       .minCells (default 1)   drop countries with fewer grid cells
%       .outDir   (default fullfile('dashboard','data'))
%       .save     (default 1)   .verbose (default 1)
%
% OUTPUT (also dashboard/data/country_series.csv when .save):
%   T - ISO3, CountryName, Year, AnnualMean, OSDMA8, nCells (ppb)
%
% Run exportCountrySeries('--selftest') to execute built-in unit checks.
%
% SEE ALSO: regionalCountrySummary, cubeAnnualMetrics, computeGridWeights

%% Self-test entry point
if nargin >= 1 && (ischar(cube) || isstring(cube)) && strcmp(cube, '--selftest')
    T = local_selftest();
    return;
end

if nargin < 3 || isempty(opts), opts = struct(); end
opts = local_defaults(opts);

M = cubeAnnualMetrics(cube);
years = M.years(:);
nY = numel(years);

iso     = string(weights.ISO3);
country = string(weights.CountryName);
wPop    = weights.w_pop(:);

% weights rows index cube cells positionally. A length mismatch means the two
% were built from different cubes, and would silently truncate or mislabel the
% country masks rather than fail.
if numel(iso) ~= cube.nGrid
    error('exportCountrySeries:gridMismatch', ...
        ['weights has %d cells but the cube has %d. They were built from ' ...
         'different cubes -- rerun computeGridWeights on this cube.'], ...
        numel(iso), cube.nGrid);
end

u = unique(iso);
u = u(u ~= "" & ~ismissing(u));

ISO3 = strings(0,1); CountryName = strings(0,1);
Year = []; AnnualMean = []; OSDMA8 = []; nCells = [];

for i = 1:numel(u)
    m = iso == u(i);
    if sum(m) < opts.minCells, continue; end
    w = wPop(m);
    if sum(w) == 0, w = ones(sum(m),1); end   % same fallback as the summary

    cn = country(m);
    a = local_wmeanCols(M.annualMean(m, :), w);   % 1 x nY
    o = local_wmeanCols(M.osdma8(m, :), w);

    ISO3        = [ISO3;        repmat(u(i),  nY, 1)];        %#ok<AGROW>
    CountryName = [CountryName; repmat(cn(1), nY, 1)];        %#ok<AGROW>
    Year        = [Year;        years];                       %#ok<AGROW>
    AnnualMean  = [AnnualMean;  a(:)];                        %#ok<AGROW>
    OSDMA8      = [OSDMA8;      o(:)];                        %#ok<AGROW>
    nCells      = [nCells;      repmat(sum(m), nY, 1)];       %#ok<AGROW>
end

T = table(ISO3, CountryName, Year, AnnualMean, OSDMA8, nCells);
T = sortrows(T, {'CountryName', 'Year'});

if opts.save
    if ~exist(opts.outDir, 'dir'), mkdir(opts.outDir); end
    writetable(T, fullfile(opts.outDir, 'country_series.csv'));
    if opts.verbose
        fprintf('exportCountrySeries: %d countries x %d years -> country_series.csv\n', ...
            numel(unique(T.ISO3)), nY);
    end
end

end

% ========================================================================
function v = local_wmeanCols(A, w)
% Weighted mean down the rows of A (nCells x nYears), NaN-safe per column.
nY = size(A, 2);
v = nan(1, nY);
for j = 1:nY
    x = A(:, j);
    ok = ~isnan(x) & ~isnan(w);
    if any(ok), v(j) = sum(w(ok) .* x(ok)) / sum(w(ok)); end
end
end

% ========================================================================
function opts = local_defaults(opts)
d = struct('minCells', 1, 'outDir', fullfile('dashboard','data'), ...
    'save', 1, 'verbose', 1);
f = fieldnames(d);
for i = 1:numel(f)
    if ~isfield(opts, f{i}) || isempty(opts.(f{i})), opts.(f{i}) = d.(f{i}); end
end
end

% ========================================================================
function ok = local_selftest()
ok = true;

% 3 cells: 2 in AAA (rising, different offsets), 1 in BBB (flat).
yrs = 2000:2009;
yr = []; mon = []; tk = [];
for y = yrs
    for m = 1:12, yr(end+1)=y; mon(end+1)=m; tk(end+1)=y+(m-1)/12; end %#ok<AGROW>
end
oz = nan(3, numel(yr));
for c = 1:numel(yr)
    yy = yr(c) - 2000;
    oz(1, c) = 30 + 2*yy;
    oz(2, c) = 32 + 2*yy;
    oz(3, c) = 25;
end
cube = struct('ozone', oz, 'year', yr, 'month', mon, 'time', tk, ...
    'nGrid', 3, 'grid', zeros(3,2));
weights = struct('ISO3', ["AAA";"AAA";"BBB"], ...
    'CountryName', ["Aaa";"Aaa";"Bbb"], 'w_pop', [1;1;1]);

T = exportCountrySeries(cube, weights, struct('save', 0, 'verbose', 0));

% one row per country-year
assert(height(T) == 2 * numel(yrs), 'row count');

A = T(T.ISO3 == "AAA", :);
A = sortrows(A, 'Year');
% equal weights on 30+2t and 32+2t -> 31+2t
expected = 31 + 2 * (0:numel(yrs)-1)';
assert(max(abs(A.AnnualMean - expected)) < 1e-9, 'AAA annual mean');

B = T(T.ISO3 == "BBB", :);
assert(all(abs(B.AnnualMean - 25) < 1e-9), 'BBB flat');
assert(all(B.nCells == 1) && all(A.nCells == 2), 'cell counts');

% agreement with regionalCountrySummary on the trailing-10-year mean
S = regionalCountrySummary(cube, weights, struct('save', 0, 'verbose', 0, ...
    'recentYears', 10));
sA = S.MeanAnnual_recent(S.ISO3 == "AAA");
assert(abs(mean(A.AnnualMean) - sA) < 1e-9, 'agrees with country summary');

fprintf('exportCountrySeries: all self-tests passed.\n');
end
