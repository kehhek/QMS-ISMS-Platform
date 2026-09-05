import React from 'react'
import DocumentsPanel from './DocumentsPanel'

// Same document-control machinery as the general Documents tab (version
// control, e-signed approval workflow, doc ID/classification/reviewer/
// approver, PDF attachment) — just scoped to its own category, so a
// policy only ever shows up here, never duplicated onto the general list.
export default function PolicyPanel({ token }) {
  return <DocumentsPanel token={token} category="policy" />
}
