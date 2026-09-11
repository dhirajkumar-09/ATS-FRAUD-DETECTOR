import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/auth'];
const PROTECTED_PREFIX = '/dashboard';

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for token in a middleware-accessible cookie (set by the auth page)
  const tokenCookie = request.cookies.get('ats-token');

  const isProtected = pathname.startsWith(PROTECTED_PREFIX);
  const isPublicAuth = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // Unauthenticated user trying to reach dashboard → redirect to /auth
  if (isProtected && !tokenCookie) {
    const url = request.nextUrl.clone();
    url.pathname = '/auth';
    return NextResponse.redirect(url);
  }

  // Authenticated user hitting /auth → redirect to dashboard
  if (isPublicAuth && tokenCookie) {
    const url = request.nextUrl.clone();
    url.pathname = '/dashboard/scan';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/auth'],
};
