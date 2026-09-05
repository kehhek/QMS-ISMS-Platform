import React from 'react'
import DocumentsPanel from './DocumentsPanel'

// See PolicyPanel — same reasoning, scoped to the "work_instruction" category.
export default function WorkInstructionPanel({ token }) {
  return <DocumentsPanel token={token} category="work_instruction" />
}
