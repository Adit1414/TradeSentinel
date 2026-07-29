import { useEffect, useRef } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';

/**
 * MACD sub-panel with MACD line, Signal line, and Histogram.
 */
export default function MACDPanel({ macdLine, macdSignal, macdHistogram }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!macdLine?.length && !macdHistogram?.length) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8892b0',
        fontFamily: "'Inter', sans-serif",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(136,146,176,0.04)' },
        horzLines: { color: 'rgba(136,146,176,0.04)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { visible: false },
        horzLine: { color: 'rgba(136,146,176,0.2)', labelBackgroundColor: '#1a2236' },
      },
      rightPriceScale: {
        borderColor: 'rgba(136,146,176,0.12)',
        scaleMargins: { top: 0.15, bottom: 0.15 },
      },
      timeScale: {
        borderColor: 'rgba(136,146,176,0.12)',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: false,
      handleScale: false,
    });

    // MACD Histogram (bar chart)
    if (macdHistogram?.length) {
      const histSeries = chart.addHistogramSeries({
        priceLineVisible: false,
        title: '',
      });
      histSeries.setData(
        macdHistogram.map((d) => ({
          time: d.time,
          value: d.value,
          color: d.value >= 0 ? 'rgba(0,230,118,0.5)' : 'rgba(255,23,68,0.5)',
        }))
      );
    }

    // MACD Line
    if (macdLine?.length) {
      const macdSeries = chart.addLineSeries({
        color: '#2979ff',
        lineWidth: 1.5,
        title: 'MACD',
        priceLineVisible: false,
      });
      macdSeries.setData(macdLine);
    }

    // Signal Line
    if (macdSignal?.length) {
      const signalSeries = chart.addLineSeries({
        color: '#ff9100',
        lineWidth: 1.5,
        title: 'Signal',
        priceLineVisible: false,
      });
      signalSeries.setData(macdSignal);
    }

    // Zero line
    if (macdLine?.length) {
      const zeroSeries = chart.addLineSeries({
        color: 'rgba(136,146,176,0.2)',
        lineWidth: 1,
        lineStyle: 2,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        title: '',
      });
      zeroSeries.setData(
        macdLine.map((d) => ({ time: d.time, value: 0 }))
      );
    }

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [macdLine, macdSignal, macdHistogram]);

  return (
    <div className="chart-pane chart-pane-sub">
      <div className="chart-pane-label">MACD (12, 26, 9)</div>
      <div ref={containerRef} className="chart-container chart-container-sub" />
    </div>
  );
}
