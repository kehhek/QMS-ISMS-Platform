import React from 'react'
import DocumentsPanel from './DocumentsPanel'

// See PolicyPanel — same reasoning, scoped to the "sop" category.
export default function SopPanel({ token }) {
  return <DocumentsPanel token={token} category="sop" />
}
