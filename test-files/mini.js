var a, b, c;
var d = 123;

function first ( x, y ){ return x * y; }

function first_again( x ){ var n = x; return n * n; }

second = function(){ return first( 23, 42 ); }

third = {
  a: 123,
  b: 456,
  c: "string",
  square: function( n ){ return n*n; },
  round: function( n ){ return this.square( n ); }
}

third.squishy = function(){ return 1; }; // comments1 { should be ignored }

fourth = function( reallylongvariablename, doesitreallymatter ){
  return third.square( 3 ); 
}

/* comments2 {
 should be ignored 
 third.squishy();
} */

