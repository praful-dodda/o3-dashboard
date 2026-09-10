function exportForDashboard(cfg)
% exportForDashboard - Build everything dashboard/data needs, in one call
%
% Run from the REPOSITORY ROOT after runPostprocess has produced 8postprocess.
% Copies the small aggregated CSVs the dashboard reads, then adds the two
% products the post-processing pipeline does not currently write:
%   country_series.csv   per-country ANNUAL SERIES (exportCountrySeries)
%   grid_annual.parquet  per-cell annual metrics   (exportGridFields)
%
% Nothing here touches the raw estimates, the 0.1 deg downscaling tree, or
% 7validation -- the dashboard never reads those.
%
% SYNTAX:
%   exportForDashboard
%   exportForDashboard(cfg)
%
% cfg (optional):
%   .cubeFile   path to a single cube .mat. Default '' = rebuild the SAME
%               per-year best-method composite runPostprocess used, via
%               loadCompositeCube + csv/best_method_by_year.csv. Do not point
%               this at one cube_*.mat unless you mean to: each cached cube
%               covers only the years of one fusion method (e.g. 1990-2004 for
%               -02), so the dashboard grid would then disagree with the CSVs.
%   .bestMethodCsv  year->method table (default 8postprocess/csv/best_method_by_year.csv)
%   .yearRange  (default [1990 2022])
%   .srcDir     estimate tree for assembleBMEcube (default 5BMEspatialPlots)
%   .fallbackMethod (default '13000313-02')
%   .weightsFile (default 8postprocess/cubes/grid_weights.mat)
%   .csvDir     (default 8postprocess/csv)
%   .outDir     (default dashboard/data)
%   .doCountry  (default true)   .doGrid (default true)   .doCopy (default true)
%
% SEE ALSO: runPostprocess, exportCountrySeries, exportGridFields

if nargin < 1 || isempty(cfg), cfg = struct(); end
d = struct( ...
    'cubeFile', '', ...
    'weightsFile', fullfile('8postprocess','cubes','grid_weights.mat'), ...
    'csvDir', fullfile('8postprocess','csv'), ...
    'outDir', fullfile('dashboard','data'), ...
    'bestMethodCsv', fullfile('8postprocess','csv','best_method_by_year.csv'), ...
    'yearRange', [1990 2022], ...
    'srcDir', '5BMEspatialPlots', ...
    'fallbackMethod', '13000313-02', ...
    'doCountry', true, 'doGrid', true, 'doCopy', true);
f = fieldnames(d);
for i = 1:numel(f)
    if ~isfield(cfg, f{i}) || isempty(cfg.(f{i})), cfg.(f{i}) = d.(f{i}); end
end

if ~exist(cfg.outDir, 'dir'), mkdir(cfg.outDir); end

%% 1. Copy the aggregated CSVs the dashboard reads directly
COPY = {'regional_series.csv', 'popweighted_annual.csv', ...
        'seasonal_means_trends.csv', 'regional_trends.csv', ...
        'trend_ols_regional.csv', 'trend_twoperiod_regional.csv', ...
        'peak_month_trend.csv', 'country_trends.csv', ...
        'exposure_by_threshold.csv', 'exposure_trends.csv'};

if cfg.doCopy
    nCopied = 0;
    for i = 1:numel(COPY)
        src = fullfile(cfg.csvDir, COPY{i});
        if exist(src, 'file')
            copyfile(src, fullfile(cfg.outDir, COPY{i}));
            nCopied = nCopied + 1;
        else
            fprintf('  missing (skipped): %s\n', src);
        end
    end
    ref = fullfile('8postprocess', 'ref_published_trends.csv');
    if exist(ref, 'file')
        copyfile(ref, fullfile(cfg.outDir, 'ref_published_trends.csv'));
        nCopied = nCopied + 1;
    end
    fprintf('exportForDashboard: copied %d/%d CSVs to %s\n', ...
        nCopied, numel(COPY) + 1, cfg.outDir);
end

%% 2. Locate the cube and weights
needCube = cfg.doCountry || cfg.doGrid;
if ~needCube, return; end

if ~exist(cfg.weightsFile, 'file')
    warning('exportForDashboard:noWeights', ...
        'grid_weights.mat not found at %s. Run computeGridWeights first.', ...
        cfg.weightsFile);
    return;
end

fprintf('exportForDashboard: weights = %s\n', cfg.weightsFile);
Sw = load(cfg.weightsFile);
weights = local_firstStructWith(Sw, 'w_pop');

if ~isempty(cfg.cubeFile)
    % Explicit single-method cube. Caller's responsibility -- this will not
    % span the full record unless that cube happens to.
    fprintf('exportForDashboard: cube    = %s (explicit)\n', cfg.cubeFile);
    if ~exist(cfg.cubeFile, 'file')
        error('exportForDashboard:noCube', 'cubeFile not found: %s', cfg.cubeFile);
    end
    Sc = load(cfg.cubeFile);
    cube = local_firstStructWith(Sc, 'ozone');
else
    % Default: rebuild the per-year best-method composite exactly as
    % runPostprocess does, so grid_annual.parquet and the copied CSVs are two
    % views of one product rather than two different ones.
    cube = local_compositeCube(cfg);
end

if isempty(cube)
    error('exportForDashboard:badCube', 'No struct with an .ozone field found.');
end
if isempty(weights)
    error('exportForDashboard:badWeights', ...
        'No struct with a .w_pop field in %s', cfg.weightsFile);
end

%% 3. The two new products
if cfg.doCountry
    exportCountrySeries(cube, weights, struct('outDir', cfg.outDir));
end
if cfg.doGrid
    exportGridFields(cube, weights, struct('outDir', cfg.outDir));
end

fprintf(['\nexportForDashboard: done. Next:\n' ...
         '  streamlit run dashboard/app.py\n']);

end

% ========================================================================
function cube = local_compositeCube(cfg)
% Rebuild runPostprocess's per-year best-method composite.
%
% There is deliberately no "pick the biggest cube_*.mat" fallback here. Each
% cached cube covers only the years one fusion method was selected for
% (13000313-02 -> 1990-2004, -06 -> 2005-2021, ...), so any single file is a
% partial record. Silently exporting one would give the dashboard a grid that
% disagrees with the CSVs sitting next to it, with nothing to flag the mismatch.
if ~exist(cfg.bestMethodCsv, 'file')
    error('exportForDashboard:noBestMethod', ...
        ['%s not found. It is written by runPostprocess step A and names ' ...
         'the fusion method for each year; without it the composite cannot ' ...
         'be rebuilt. Run runPostprocess, or pass cfg.bestMethodCsv.'], ...
        cfg.bestMethodCsv);
end

bestT = loadBestMethodCsv(cfg.bestMethodCsv, cfg.yearRange);
lcfg = struct( ...
    'methodConfig', struct('goScenario', 3, 'logTransf', 0, 'areaCode', 0, ...
                           'mapResolution', 1.0, 'dataFormat', 'stug', ...
                           'keepOnlyLand', 1), ...
    'fallbackMethod', cfg.fallbackMethod, ...
    'srcDir', cfg.srcDir, ...
    'outDir', '8postprocess', ...
    'yearRange', cfg.yearRange);

fprintf('exportForDashboard: composing %d-%d best-method cube...\n', ...
    cfg.yearRange(1), cfg.yearRange(2));
cube = loadCompositeCube(lcfg, bestT);
fprintf('exportForDashboard: cube    = composite, %d cells x %d months\n', ...
    cube.nGrid, cube.nMonths);
end

% ========================================================================
function s = local_firstStructWith(S, fieldName)
% .mat files here save the struct under varying names; find it by shape.
s = [];
names = fieldnames(S);
for i = 1:numel(names)
    v = S.(names{i});
    if isstruct(v) && isfield(v, fieldName), s = v; return; end
end
end
