# Diagnostic refinement after the first tracing failures

21 November 2026, while the original suite was still running: the four coarse
fields showed standard-tolerance adaptive flux drift above the new 1e-7 limit,
and several standard/tight length differences exceeded 0.1 mm. The tight
solutions agreed much more closely with the old RK4 heat projection than these
precision failures alone might suggest.

Add a bounded third-tolerance diagnostic at the pre-existing representative
1 mm offset in all eight fields: rtol 1e-12, atol (1e-13, 1e-13, 1e-11), maximum
toroidal-angle step 0.025 rad. Compare it against the already frozen tight
solution using the same 10 micrometre, 0.1 mm and 0.1% limits, and keep the
same 1e-7 flux-conservation limit. This is a post hoc precision diagnosis,
not a replacement of the initial tests, a threshold change, a full correction
of all dense samples, or an independent physics validation. Preserve all initial
failures and leave their initial overall result unchanged.
