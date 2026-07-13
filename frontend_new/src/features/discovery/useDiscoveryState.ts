import { startTransition, useEffect, useState } from 'react';
import { PAGE_SIZE } from '../../domain/madplan/constants';
import type { DiscoveryDateFilter, DiscoveryState, DiscoveryView } from '../../domain/madplan/types';

const DEFAULT_STATE: DiscoveryState = {
  query: '',
  source: null,
  category: null,
  dateFilter: 'all',
  freeOnly: false,
  zone: null,
  view: 'list',
  showCount: PAGE_SIZE,
};

function sanitizeDateFilter(value: string | null): DiscoveryDateFilter {
  if (value === 'today' || value === 'weekend' || value === 'week' || value === 'month') return value;
  return 'all';
}

function sanitizeView(value: string | null): DiscoveryView {
  if (value === 'map' || value === 'news') return value;
  return 'list';
}

function readInitialState(): DiscoveryState {
  const params = new URLSearchParams(window.location.search);

  return {
    query: params.get('q') || '',
    source: params.get('source'),
    category: params.get('category'),
    dateFilter: sanitizeDateFilter(params.get('when')),
    freeOnly: params.get('free') === '1',
    zone: params.get('zone'),
    view: sanitizeView(params.get('view')),
    showCount: PAGE_SIZE,
  };
}

function writeStateToUrl(state: DiscoveryState) {
  const params = new URLSearchParams();

  if (state.query) params.set('q', state.query);
  if (state.source) params.set('source', state.source);
  if (state.category) params.set('category', state.category);
  if (state.dateFilter !== 'all') params.set('when', state.dateFilter);
  if (state.freeOnly) params.set('free', '1');
  if (state.zone) params.set('zone', state.zone);
  if (state.view !== 'list') params.set('view', state.view);

  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}`;
  window.history.replaceState(null, '', nextUrl);
}

export function useDiscoveryState() {
  const [state, setState] = useState<DiscoveryState>(readInitialState);

  useEffect(() => {
    writeStateToUrl(state);
  }, [state]);

  function patch(partial: Partial<DiscoveryState>, resetCount = true) {
    startTransition(() => {
      setState((current) => ({
        ...current,
        ...partial,
        showCount: resetCount ? PAGE_SIZE : (partial.showCount ?? current.showCount),
      }));
    });
  }

  return {
    state,
    setQuery: (query: string) => patch({ query }),
    setSource: (source: string | null) => patch({ source }),
    setCategory: (category: string | null) => patch({ category }),
    setDateFilter: (dateFilter: DiscoveryDateFilter) => patch({ dateFilter }),
    setFreeOnly: (freeOnly: boolean) => patch({ freeOnly }),
    setZone: (zone: string | null) => patch({ zone }),
    setView: (view: DiscoveryView) => patch({ view }, false),
    loadMore: () => setState((current) => ({ ...current, showCount: current.showCount + PAGE_SIZE })),
    clearAll: () => setState(DEFAULT_STATE),
  };
}

