import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { MarketHero } from './components/MarketHero';
import { FareMovementChart } from './components/FareMovementChart';
import { FareDistributionChart } from './components/FareDistributionChart';
import { BookingCurveChart } from './components/BookingCurveChart';
import { TodaysMarketSection } from './components/TodaysMarketSection';
import { MethodologyModal } from './components/MethodologyModal';
import { api } from './api/client';
import { AlertTriangle } from 'lucide-react';

const SECTIONS = ['overview', 'movement', 'distribution', 'booking', 'observed-fares'];

export default function App() {
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState('HYD-DEL'); // Default to HYD-DEL
  const [selectedBucket, setSelectedBucket] = useState('7D');    // Default to Near-term (1–10D)
  const [nationalData, setNationalData] = useState(null);
  const [nearTermTrendData, setNearTermTrendData] = useState(null);       // Fixed 1–10D near-term trend (immune to bucket selection)
  const [distributionTrendData, setDistributionTrendData] = useState(null); // Dynamic bucket-specific trend for distribution
  const [movementData, setMovementData] = useState(null);
  const [routeSummaries, setRouteSummaries] = useState([]);
  const [bookingCurveData, setBookingCurveData] = useState(null);
  const [latestFaresData, setLatestFaresData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [globalError, setGlobalError] = useState(null);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('overview');

  // Load all primary data from backend API when selectedRoute changes or refreshed
  const loadDashboardData = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setIsRefreshing(true);
    setGlobalError(null);

    try {
      // 1. Load Routes, Summaries, and National Composite
      const [availableRoutes, summaries, national] = await Promise.all([
        api.getRoutes().catch(() => []),
        api.getRoutesSummary().catch(() => []),
        api.getNationalIndex().catch(() => null),
      ]);

      setRoutes(availableRoutes || []);
      setRouteSummaries(summaries || []);
      setNationalData(national);

      const targetRoute = selectedRoute || (availableRoutes.length > 0 ? availableRoutes[0] : 'HYD-DEL');

      // 2. Load Route Context Data (or National Data)
      if (selectedRoute) {
        const [fixedNearTerm, dynamicDistTrend, bc, latest, mov] = await Promise.all([
          api.getRouteTrend(selectedRoute, '7D').catch(() => null),             // Fixed near-term (1–10D)
          api.getRouteTrend(selectedRoute, selectedBucket).catch(() => null),    // Dynamic distribution bucket
          api.getRouteBookingCurve(selectedRoute).catch(() => null),
          api.getLatestPrices(selectedRoute).catch(() => null),
          api.getRouteMovement(selectedRoute).catch(() => null),
        ]);
        setNearTermTrendData(fixedNearTerm);
        setDistributionTrendData(dynamicDistTrend);
        setBookingCurveData(bc);
        setLatestFaresData(latest);
        setMovementData(mov);
      } else {
        // Tracked-route composite view
        const [bc, latest] = await Promise.all([
          api.getBookingCurve().catch(() => null),
          targetRoute ? api.getLatestPrices(targetRoute).catch(() => null) : Promise.resolve(null),
        ]);
        setNearTermTrendData(null);
        setDistributionTrendData(null);
        setBookingCurveData(bc);
        setLatestFaresData(latest);
        setMovementData(null);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      setGlobalError(err.message || 'Failed to connect to FareIndex India backend');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedRoute]);

  // Initial load and on route change
  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Dynamic distribution bucket change effect (does NOT alter Overview hero)
  useEffect(() => {
    if (selectedRoute && selectedBucket) {
      api.getRouteTrend(selectedRoute, selectedBucket)
        .then((trend) => setDistributionTrendData(trend))
        .catch((err) => console.error('Failed to load distribution trend for bucket:', err));
    }
  }, [selectedRoute, selectedBucket]);

  // Scroll spy to update active section in header
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const offset = 180;

      for (let i = SECTIONS.length - 1; i >= 0; i--) {
        const el = document.getElementById(SECTIONS[i]);
        if (el) {
          const top = el.offsetTop - offset;
          if (scrollY >= top) {
            setActiveSection(SECTIONS[i]);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Handle section navigation
  const handleNavigate = useCallback((sectionId) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveSection(sectionId);
      window.history.replaceState(null, '', `#${sectionId}`);
    }
  }, []);

  // Current route summary
  const currentRouteSummary = useMemo(() => {
    if (!selectedRoute) return null;
    return routeSummaries.find((s) => s.route === selectedRoute);
  }, [selectedRoute, routeSummaries]);

  // Latest observation date label derived dynamically
  const lastObsDate = useMemo(() => {
    if (currentRouteSummary?.latest_observation_date) {
      return currentRouteSummary.latest_observation_date;
    }
    if (nationalData?.latest_value?.observation_date) {
      return nationalData.latest_value.observation_date;
    }
    if (routeSummaries.length > 0 && routeSummaries[0].latest_observation_date) {
      return routeSummaries[0].latest_observation_date;
    }
    return null;
  }, [currentRouteSummary, nationalData, routeSummaries]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-teal-500/20 selection:text-teal-900">
      {/* 1. TOP NAVIGATION HEADER */}
      <Header
        lastObservationDate={lastObsDate}
        onRefresh={() => loadDashboardData(true)}
        isRefreshing={isRefreshing}
        onOpenMethodology={() => setIsMethodologyOpen(true)}
        activeSection={activeSection}
        onNavigate={handleNavigate}
      />

      {/* Main Content Area: Focused Customer Hierarchy */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-14">
        {/* Global Error Banner */}
        {globalError && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono flex items-center justify-between shadow-2xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{globalError} — Ensure the backend service is running on port 8000.</span>
            </div>
            <button
              onClick={() => loadDashboardData(true)}
              className="px-3 py-1 bg-rose-100 hover:bg-rose-200 text-rose-900 rounded-lg border border-rose-300 text-xs font-semibold cursor-pointer"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* 1–4. HERO: ROUTE + AVERAGE OBSERVED FARE + MOVEMENT + TYPICAL FARE + FARE POSITION */}
        <MarketHero
          routes={routes}
          selectedRoute={selectedRoute}
          onSelectRoute={(r) => setSelectedRoute(r)}
          routeSummaries={routeSummaries}
          nationalData={nationalData}
          nearTermTrendData={nearTermTrendData}
          movementData={movementData}
          onOpenMethodology={() => setIsMethodologyOpen(true)}
        />

        {/* 5. HISTORICAL FARE MOVEMENT (MAIN GRAPH) */}
        <section id="movement">
          <FareMovementChart
            movementData={movementData}
            selectedRoute={selectedRoute}
            isNational={selectedRoute === null}
          />
        </section>

        {/* 6. FARE DISTRIBUTION (WHERE OBSERVED FARES CLUSTER) */}
        <section id="distribution">
          {!selectedRoute ? null : (
            <FareDistributionChart
              distributionData={distributionTrendData?.distribution}
              route={selectedRoute}
              leadTimeLabel={distributionTrendData?.lead_time_label || 'Near-term · 1–10 days ahead'}
              leadTimeBucket={selectedBucket}
            />
          )}
        </section>

        {/* 7. BOOKING BEHAVIOUR (7D, 14D, 21D, 30D, 60D LEAD TIME CURVE) */}
        <section id="booking">
          <BookingCurveChart
            bookingData={bookingCurveData}
            route={selectedRoute}
            selectedBucket={selectedBucket}
            onSelectBucket={(b) => setSelectedBucket(b)}
          />
        </section>

        {/* 8. OBSERVED FARES (REPRESENTATIVE CURRENT FLIGHT OPTIONS) */}
        <TodaysMarketSection
          latestFaresData={latestFaresData}
          selectedRoute={selectedRoute}
          typicalFare={currentRouteSummary?.near_term_median || nearTermTrendData?.current_typical_fare || 9268}
          selectedBucket={selectedBucket}
        />
      </main>

      {/* 5-Step Methodology Modal (How is this calculated?) */}
      <MethodologyModal
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />

      {/* 9. METHODOLOGY & DATA FRESHNESS FOOTER */}
      <footer className="border-t border-slate-200/90 bg-white py-8 px-6 text-xs text-slate-500 mt-12">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-600" />
            <span className="font-extrabold text-slate-950 text-sm">FareIndex India</span>
            <span className="text-slate-400 font-normal">— Understand what an airfare means</span>
          </div>

          <div className="flex items-center gap-6 font-medium text-slate-600">
            <button
              onClick={() => setIsMethodologyOpen(true)}
              className="hover:text-teal-800 transition-colors cursor-pointer inline-flex items-center gap-1 font-semibold text-teal-850"
            >
              <span>How is this calculated?</span>
            </button>
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            Domestic · One-way · Economy · 1 adult · INR
          </div>
        </div>
      </footer>
    </div>
  );
}
