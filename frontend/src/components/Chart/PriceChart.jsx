import { useEffect, useRef, useMemo } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import './Chart.css';

/**
 * Main candlestick chart with VWAP/EMA and Supertrend overlays.
 */
export default function PriceChart({ candles, indicators, mode }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !candles?.length) return;

    // Create chart
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8892b0',
        fontFamily: "'Inter', sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(136,146,176,0.06)' },
        horzLines: { color: 'rgba(136,146,176,0.06)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(136,146,176,0.3)', labelBackgroundColor: '#1a2236' },
        horzLine: { color: 'rgba(136,146,176,0.3)', labelBackgroundColor: '#1a2236' },
      },
      rightPriceScale: {
        borderColor: 'rgba(136,146,176,0.12)',
        scaleMargins: { top: 0.05, bottom: 0.05 },
      },
      timeScale: {
        borderColor: 'rgba(136,146,176,0.12)',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { vertTouchDrag: false },
    });

    chartRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00e676',
      downColor: '#ff1744',
      borderUpColor: '#00e676',
      borderDownColor: '#ff1744',
      wickUpColor: '#00e676',
      wickDownColor: '#ff1744',
    });
    candleSeries.setData(candles);

    // VWAP / EMA overlay
    const overlayKey = mode === 'long_term' ? 'ema_200' : 'vwap';
    const overlayData = indicators?.[overlayKey];
    if (overlayData?.length) {
      const overlaySeries = chart.addLineSeries({
        color: '#7c4dff',
        lineWidth: 2,
        lineStyle: 0,
        title: overlayKey === 'ema_200' ? '200 EMA' : 'VWAP',
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      overlaySeries.setData(overlayData);
    }

    // Supertrend overlay (colored segments)
    const supertrendData = indicators?.supertrend;
    if (supertrendData?.length) {
      // Split into green and red segments
      const greenData = [];
      const redData = [];

      supertrendData.forEach((point) => {
        if (point.color === '#00e676') {
          greenData.push({ time: point.time, value: point.value });
          redData.push({ time: point.time, value: NaN });
        } else {
          redData.push({ time: point.time, value: point.value });
          greenData.push({ time: point.time, value: NaN });
        }
      });

      // We'll use a single series with the dominant color, since LW Charts
      // doesn't support per-point coloring natively — use a line series
      const stSeries = chart.addLineSeries({
        color: '#ffab00',
        lineWidth: 2,
        lineStyle: 2,
        title: 'Supertrend',
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      stSeries.setData(
        supertrendData.map((p) => ({ time: p.time, value: p.value }))
      );
    }

    // Fit content
    chart.timeScale().fitContent();

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [candles, indicators, mode]);

  return (
    <div className="chart-pane chart-pane-main">
      <div ref={containerRef} className="chart-container" />
    </div>
  );
}
