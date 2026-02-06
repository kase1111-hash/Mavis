/**
 * Sheet Text display component.
 *
 * Renders the song's Sheet Text with monospace formatting.
 */

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function SheetTextView({ text = '' }) {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#16213e',
    borderRadius: 4,
    padding: 12,
    minHeight: 60,
  },
  text: {
    color: '#eee',
    fontFamily: 'monospace',
    fontSize: 16,
    lineHeight: 28,
  },
});
