const command = (name, label, source = 'muster_builtin') => ({
  name,
  label,
  description: `${label} command`,
  source,
  surfaces: ['gameplan_workspace'],
})

const commands = [
  command('tokens', 'Token ledger'),
  command('usage', 'My usage'),
  command('sessions', 'Sessions'),
  command('artifacts', 'Artifacts'),
  command('reports', 'Governance reports'),
  command('limits', 'Rate limits'),
  command('audit', 'Audit trail'),
  command('security', 'Security posture'),
  command('evals', 'Evaluation gates'),
  command('approvals', 'Approvals'),
  command('validation_status', 'Validation status'),
  command('release_evidence', 'Release evidence'),
  command('documentation_status', 'Documentation status'),
  command('status', 'Runtime status'),
  command('providers', 'Providers'),
  command('models', 'Models'),
  command('tools', 'Tools'),
  command('skills', 'Skills'),
  command('plugins', 'Plugins'),
  command('mcp', 'MCP servers'),
  command('channels', 'Channels'),
  command('agents', 'Agents'),
]

function interceptWorkspace(accessTier, turns = []) {
  cy.intercept('POST', '**/api/method/quant_customizations.api.openclaw_ai.get_command_catalog', {
    statusCode: 200,
    body: {
      message: {
        context: { access_tier: accessTier, user: 'test@example.com' },
        commands,
        personas: {
          tester: {
            label: 'Tester',
            description: 'Adversarial QA agent',
            source: 'muster_builtin',
          },
        },
      },
    },
  }).as('catalog')
  cy.intercept('POST', '**/api/method/quant_customizations.api.openclaw_ai.get_run_history', {
    statusCode: 200,
    body: { message: { turns } },
  }).as('history')
}

describe('Muster governance workspace', () => {
  beforeEach(() => {
    cy.login('Administrator', Cypress.env('MUSTER_QA_PASSWORD') || 'admin')
  })

  it('shows role-scoped control groups and keeps one navigable command overlay', () => {
    interceptWorkspace('permission_manager')
    cy.visit('/g/muster')
    cy.wait(['@catalog', '@history'])

    cy.get('[data-testid="muster-control-center"]')
      .should('be.visible')
      .and('have.attr', 'data-access-tier', 'permission_manager')
    cy.get('[data-testid="muster-control-tab-governance"]').should(
      'have.attr',
      'aria-selected',
      'true',
    )
    cy.get('[data-testid="muster-command-reports"]').should('be.visible')

    cy.get('[data-testid="muster-control-tab-personal"]').click()
    cy.get('[data-testid="muster-command-tokens"]').should('be.visible')
    cy.get('[data-testid="muster-control-tab-runtime"]').click()
    cy.get('[data-testid="muster-command-status"]').should('be.visible')

    cy.get('[contenteditable="true"]').click().type('/')
    cy.get('[role="listbox"][aria-label="Muster suggestions"]').should('have.length', 1)
    cy.get('[contenteditable="true"]').type('{downarrow}{downarrow}{downarrow}{uparrow}')
    cy.get('[role="listbox"][aria-label="Muster suggestions"]').should('have.length', 1)
    cy.get('[role="option"][aria-selected="true"]').should('have.length', 1)
    cy.get('[contenteditable="true"]').type('{esc}')
    cy.get('[role="listbox"][aria-label="Muster suggestions"]').should('not.exist')
    cy.get('[contenteditable="true"]').should('contain.text', '/')
  })

  it('does not expose governance actions to an ordinary user', () => {
    interceptWorkspace('user')
    cy.visit('/g/muster?role=user')
    cy.wait(['@catalog', '@history'])

    cy.get('[data-testid="muster-control-center"]').should('have.attr', 'data-access-tier', 'user')
    cy.get('[data-testid="muster-control-tab-personal"]').should(
      'have.attr',
      'aria-selected',
      'true',
    )
    cy.get('[data-testid="muster-control-tab-governance"]').should('not.exist')
    cy.get('[data-testid="muster-command-reports"]').should('not.exist')
    cy.get('[data-testid="muster-control-tab-runtime"]').should('exist')
  })

  it('renders evidence as metrics, tables, links, and governed follow-up actions', () => {
    interceptWorkspace('permission_manager', [
      {
        run: 'RUN-1',
        prompt: '/reports',
        final_text: 'Governance report ready.',
        presentation: {
          kind: 'report',
          title: 'Usage and governance',
          summary: 'Permission-scoped evidence for this user.',
          audience: 'admin',
          kpis: [
            { label: 'Runs', value: '42' },
            { label: 'Policy blocks', value: '3', tone: 'warning' },
          ],
          tables: [
            {
              id: 'usage',
              title: 'Recent usage',
              columns: ['User', 'Tokens', 'Open'],
              rows: [['test@example.com', '1,250', '/app/openclaw-ai-run/RUN-1']],
              pagination: { page: 1, pageSize: 20, totalRows: 1 },
            },
          ],
          actions: [{ id: 'audit', label: 'Open audit', command: '/audit', style: 'primary' }],
          privacy: { rawPromptsIncluded: false, note: 'Raw prompts are hidden.' },
        },
      },
    ])
    cy.visit('/g/muster?presentation=1')
    cy.wait(['@catalog', '@history'])

    cy.contains('h3', 'Usage and governance').should('be.visible')
    cy.contains('strong', '42').should('be.visible')
    cy.contains('th', 'Tokens').should('be.visible')
    cy.get('a[href="/app/openclaw-ai-run/RUN-1"]').should('have.attr', 'target', '_blank')
    cy.contains('button', 'Open audit').should('be.visible')
    cy.contains('Raw prompts are hidden.').should('be.visible')
  })
})
