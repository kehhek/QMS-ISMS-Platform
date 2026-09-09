import React from 'react'
import StaticPageLayout from './StaticPageLayout'

export default function PrivacyPolicyPage() {
  return (
    <StaticPageLayout title="Privacy Policy">
      <p className="static-page-updated">Last updated: September 8, 2026</p>

      <p>
        This Privacy Policy explains how QISMS ("we," "us," or "our") collects, uses, and protects
        information when you use our document control, risk, and compliance management platform
        (the "Service").
      </p>

      <h2>Information we collect</h2>
      <p>We collect the following categories of information:</p>
      <ul>
        <li>
          <strong>Account information</strong> — name, email address, and role, provided when you or
          your organization creates an account.
        </li>
        <li>
          <strong>Organizational content</strong> — documents, policies, risk records, audit findings,
          evidence files, and other content your organization stores in the Service to run its
          management system.
        </li>
        <li>
          <strong>Usage and audit data</strong> — logins, actions taken, and approvals/signatures,
          retained in an append-only audit trail as part of the compliance features of the Service.
        </li>
        <li>
          <strong>Contact form submissions</strong> — information you voluntarily submit through our
          demo request or contact forms, such as your name, email, and message.
        </li>
      </ul>

      <h2>How we use information</h2>
      <p>We use the information we collect to:</p>
      <ul>
        <li>Provide, maintain, and secure the Service;</li>
        <li>Authenticate users and enforce role-based access within each organization's account;</li>
        <li>Respond to support, demo, and contact requests;</li>
        <li>Maintain the audit trails required by the compliance frameworks the Service supports; and</li>
        <li>Comply with legal obligations.</li>
      </ul>

      <h2>Data security</h2>
      <p>
        Each organization's data is isolated from every other organization's. Sensitive files (such as
        evidence attachments) are encrypted at rest, and access to organizational data is restricted by
        role. No system is completely secure, but we take reasonable technical and organizational
        measures to protect information in our care.
      </p>

      <h2>Data retention</h2>
      <p>
        We retain organizational content and audit records for as long as an account remains active, or
        as needed to meet the record-retention expectations of the compliance frameworks the Service
        supports. You may request deletion of your account information by contacting us, subject to any
        retention we're required to keep for audit or legal purposes.
      </p>

      <h2>Sharing of information</h2>
      <p>
        We do not sell personal information. We do not share your organization's content with other
        organizations using the Service. We may share information with service providers who help us
        operate the Service (e.g. hosting and storage providers), under obligations to protect it, or
        where required by law.
      </p>

      <h2>Your choices</h2>
      <p>
        You may request access to, correction of, or deletion of your personal information by
        contacting us using the details below. Your organization's administrator may also be able to
        make these changes directly within the Service.
      </p>

      <h2>Contact us</h2>
      <p>
        Questions about this Privacy Policy can be sent to{' '}
        <a href="mailto:keh@qisms.com">keh@qisms.com</a>.
      </p>
    </StaticPageLayout>
  )
}
