function T = exportGridFields(cube, weights, opts)
% exportGridFields - Per-cell, per-year metrics as a compact table for the maps
%
% Flattens cubeAnnualMetrics into long format (one row per grid cell per year)
% with the cell coordinates attached, so the dashboard can draw any annual
% field without ever opening a .mat file or the downscaled trees.
%
% Written as Parquet when parquetwrite is available (roughly 8-12 MB for
% 18k cells x 33 years), otherwise gzip-free CSV as a fallback.
%
% SYNTAX:
%   T = exportGridFields(cube, weights)
%   T = exportGridFields(cube, weights, opts)
%
% INPUTS:
%   cube    - from assembleBMEcube (or composeBestMethodCube)
%   weights - from computeGridWeights (for lon/lat and region labels);
%             pass [] to take coordinates from cube.grid
%   opts    - (optional):
%       .metrics  (default {'AnnualMean','OSDMA8','DJF','MAM','JJA','SON',
%                           'SeasonAmp','PeakMonth'})
%       .decimals (default 2)   rounding, keeps the file small
%       .outDir   (default fullfile('dashboard','data'))
%       .save     (default 1)   .verbose (default 1)
%
% OUTPUT (also dashboard/data/grid_annual.parquet when .save):
%   T - lon, lat, Year, <metrics...>  (ppb, except PeakMonth in 1-12)
%
% Run exportGridFields('--selftest') to execute built-in unit checks.
%
% SEE ALSO: cubeAnnualMetrics, computeGridWeights, exportCountrySeries

%% Self-test entry point
if nargin >= 1 && (ischar(cube) || isstring(cube)) && strcmp(cube, '--selftest')
    T = local_selftest();
    return;
end

if nargin < 2, weights = []; end
if nargin < 3 || isempty(opts), opts = struct(); end
opts = local_defaults(opts);

M = cubeAnnualMetrics(cube);
years = M.years(:);
nY = numel(years);

% Coordinates come from the cube, never from weights: the metric arrays in M
% are nGrid x nY on the CUBE's lattice, so borrowing coordinates from a weights
% struct built for a different cube would silently mislabel every cell.
lon = cube.grid(:, 1); lat = cube.grid(:, 2);
nG = numel(lon);

if ~isempty(weights) && isfield(weights, 'lon') && numel(weights.lon) ~= nG
    error('exportGridFields:gridMismatch', ...
        ['weights has %d cells but the cube has %d. They were built from ' ...
         'different cubes -- rerun computeGridWeights on this cube.'], ...
        numel(weights.lon), nG);
end

% field name in M for each requested output column
srcMap = struct('AnnualMean','annualMean', 'OSDMA8','osdma8', ...
    'DJF','DJF', 'MAM','MAM', 'JJA','JJA', 'SON','SON', ...
    'SeasonAmp','seasonAmp', 'PeakMonth','peakMonth');

% long format: cell-major within each year
T = table(repmat(lon, nY, 1), repmat(lat, nY, 1), ...
    repelem(years, nG), 'VariableNames', {'lon','lat','Year'});

kept = {};
for i = 1:numel(opts.metrics)
    name = opts.metrics{i};
    if ~isfield(srcMap, name) || ~isfield(M, srcMap.(name))
        if opts.verbose
            fprintf('exportGridFields: skipping unavailable metric %s\n', name);
        end
        continue;
    end
    A = M.(srcMap.(name));                    % nG x nY
    v = reshape(A, [], 1);                    % matches repelem(years, nG)
    if ~strcmp(name, 'PeakMonth')
        v = round(v, opts.decimals);
    end
    T.(name) = v;
    kept{end+1} = name; %#ok<AGROW>
end

% drop rows with no data at all (ocean / never-estimated cells)
if ~isempty(kept)
    allNaN = true(height(T), 1);
    for i = 1:numel(kept), allNaN = allNaN & isnan(T.(kept{i})); end
    T(allNaN, :) = [];
end

if opts.save
    if ~exist(opts.outDir, 'dir'), mkdir(opts.outDir); end
    target = fullfile(opts.outDir, 'grid_annual.parquet');
    wrote = false;
    if exist('parquetwrite', 'file') == 2
        try
            parquetwrite(target, T);
            wrote = true;
        catch err
            warning('exportGridFields:parquet', ...
                'parquetwrite failed (%s); falling back to CSV.', err.message);
        end
    end
    if ~wrote
        target = fullfile(opts.outDir, 'grid_annual.csv');
        writetable(T, target);
    end
    if opts.verbose
        d = dir(target);
        fprintf('exportGridFields: %d rows (%d cells x %d years) -> %s (%.1f MB)\n', ...
            height(T), nG, nY, target, d.bytes / 1e6);
    end
end

end

% ========================================================================
function opts = local_defaults(opts)
d = struct('metrics', {{'AnnualMean','OSDMA8','DJF','MAM','JJA','SON', ...
                        'SeasonAmp','PeakMonth'}}, ...
    'decimals', 2, 'outDir', fullfile('dashboard','data'), ...
    'save', 1, 'verbose', 1);
f = fieldnames(d);
for i = 1:numel(f)
    if ~isfield(opts, f{i}) || isempty(opts.(f{i})), opts.(f{i}) = d.(f{i}); end
end
end

% ========================================================================
function ok = local_selftest()
ok = true;

yrs = 2000:2004;
yr = []; mon = [];
for y = yrs
    for m = 1:12, yr(end+1)=y; mon(end+1)=m; end %#ok<AGROW>
end
nG = 4;
oz = nan(nG, numel(yr));
for c = 1:numel(yr)
    oz(:, c) = (25:5:40)' + (yr(c) - 2000);
end
grid = [0 0; 10 0; 20 10; 30 20];
cube = struct('ozone', oz, 'year', yr, 'month', mon, ...
    'time', yr + (mon-1)/12, 'nGrid', nG, 'grid', grid);

T = exportGridFields(cube, [], struct('save', 0, 'verbose', 0));

assert(height(T) == nG * numel(yrs), 'row count');
assert(all(ismember({'lon','lat','Year','AnnualMean'}, T.Properties.VariableNames)), ...
    'expected columns');

% coordinates must stay attached to the right cell in every year
for y = yrs
    sub = T(T.Year == y, :);
    assert(isequal(sub.lon, grid(:,1)) && isequal(sub.lat, grid(:,2)), ...
        'coordinate alignment');
    assert(max(abs(sub.AnnualMean - ((25:5:40)' + (y - 2000)))) < 1e-9, ...
        'value alignment');
end

fprintf('exportGridFields: all self-tests passed.\n');
end
