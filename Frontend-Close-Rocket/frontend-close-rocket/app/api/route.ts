export async function GET() {
  const res = await fetch("http://localhost:8000/predict?x=5");
  const data = await res.json();
  return Response.json(data);
} 