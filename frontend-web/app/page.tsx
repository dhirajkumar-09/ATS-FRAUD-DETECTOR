import { redirect } from 'next/navigation';

export default function HomePage() {
  // Root always redirects — actual destination chosen by middleware
  redirect('/auth');
}
