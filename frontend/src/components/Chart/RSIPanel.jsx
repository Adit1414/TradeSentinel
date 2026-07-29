import { useEffect, useRef } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';

/**
 * RSI sub-panel chart with reference lines at 30, 50, 70.
 */
export default function RSIPanel({ data }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !data?.length) return;

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
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: 'rgba(136,146,176,0.12)',
        visible: false,
      },
      handleScroll: false,
      handleScale: false,
    });

    // RSI line
    const rsiSeries = chart.addLineSeries({
      color: '#7c4dff',
      lineWidth: 1.5,
      title: 'RSI (14)',
      priceLineVisible: false,
    });
    rsiSeries.setData(data);

    // Reference lines (using price lines)
    rsiSeries.createPriceLine({
      price: 70,
      color: 'rgba(255,23,68,0.4)',
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: '',
    });
    rsiSeries.createPriceLine({
      price: 50,
      color: 'rgba(136,146,176,0.3)',
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: '',
    });
    rsiSeries.createPriceLine({
      price: 30,
      color: 'rgba(0,230,118,0.4)',
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: '',
    });

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
  }, [data]);

  return (
    <div className="chart-pane chart-pane-sub">
      <div className="chart-pane-label">RSI (14)</div>
      <div ref={containerRef} className="chart-container chart-container-sub" />
    </div>
  );
}
