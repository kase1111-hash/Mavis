/**
 * Buffer level display component.
 *
 * Shows input and output buffer bars with color-coded status.
 */

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

const STATUS_COLORS = {
  optimal: '#4ade80',
  overflow: '#facc15',
  underflow: '#ef4444',
};

export default function BufferDisplay({ inputLevel = 0, outputLevel = 0, outputStatus = 'underflow' }) {
  const inputPct = Math.round(inputLevel * 100);
  const outputPct = Math.round(outputLevel * 100);
  const barColor = STATUS_COLORS[outputStatus] || STATUS_COLORS.underflow;

  return (
    <View style={styles.container}>
      <View style={styles.bufferRow}>
        <Text style={styles.label}>IN</Text>
        <View style={styles.barBg}>
          <View style={[styles.barFill, { width: `${inputPct}%`, backgroundColor: '#4ade80' }]} />
        </View>
        <Text style={styles.pct}>{inputPct}%</Text>
      </View>
      <View style={styles.bufferRow}>
        <Text style={styles.label}>OUT</Text>
        <View style={styles.barBg}>
          <View style={[styles.barFill, { width: `${outputPct}%`, backgroundColor: barColor }]} />
        </View>
        <Text style={styles.pct}>{outputPct}%</Text>
        <View style={[styles.badge, { backgroundColor: barColor }]}>
          <Text style={styles.badgeText}>{outputStatus}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
  },
  bufferRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: {
    width: 32,
    color: '#eee',
    fontWeight: 'bold',
    fontFamily: 'monospace',
    fontSize: 12,
    textAlign: 'right',
    marginRight: 8,
  },
  barBg: {
    flex: 1,
    height: 16,
    backgroundColor: '#333',
    borderRadius: 3,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 3,
  },
  pct: {
    width: 40,
    color: '#eee',
    fontFamily: 'monospace',
    fontSize: 12,
    textAlign: 'right',
    marginLeft: 6,
  },
  badge: {
    borderRadius: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginLeft: 6,
  },
  badgeText: {
    color: '#000',
    fontFamily: 'monospace',
    fontSize: 10,
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
});
